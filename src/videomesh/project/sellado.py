"""Sellado atomico del paquete — V5, V7 y D29.

El orden es contrato, no recomendacion:

    escribir artifacts -> cerrarlos -> calcular bytes y sha256 -> construir
    manifest con los hashes -> state: SEALED -> escribir el manifest EL ULTIMO
    -> cerrarlo -> rename atomico del directorio

Dos exigencias son **de este lado y solo de este lado**, porque el consumidor no
puede comprobarlas: que el temporal y el destino resuelvan al mismo volumen,
verificado **antes** de empezar, y que el destino no exista ya. Nunca se cae en
silencio a copiar y borrar manteniendo la etiqueta de atomico.

Lo que se promete es **visibilidad atomica**: el consumidor ve el estado anterior
o el paquete sellado completo. No durabilidad ante caida — `fsync` y las
semanticas de sistemas de ficheros en red quedan fuera del contrato y no bloquean
`cube-v1`.
"""

import pathlib
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from videomesh.contracts.sobre import PAQUETE_DE_RECONSTRUCCION, sobre_de, volcar_documento
from videomesh.domain.camera import comprobar_camaras
from videomesh.domain.errores import ErrorDePaquete
from videomesh.domain.frames import comprobar_frame_graph
from videomesh.domain.scale import comprobar_escala
from videomesh.project.package import comprobar_integridad, comprobar_rutas, describir_artifact

__all__ = [
    "ErrorDeSellado",
    "Publicacion",
    "PublicacionAtomicaNoDisponible",
    "comprobar_mismo_volumen",
    "publicar_paquete",
]

MANIFEST = "manifest.json"


class ErrorDeSellado(ErrorDePaquete, RuntimeError):
    """El paquete no se puede publicar tal y como se ha pedido."""


class PublicacionAtomicaNoDisponible(ErrorDeSellado):
    """No se puede garantizar el rename atomico, asi que no se intenta nada."""


def comprobar_mismo_volumen(*, dispositivo_temporal: int, dispositivo_destino: int) -> None:
    """El temporal y el destino tienen que estar en el mismo sistema de ficheros.

    Recibe los dispositivos en vez de las rutas a proposito: el caso que la rompe
    se escribe sin necesitar dos discos, y lo que esta bajo prueba es la politica.
    """
    if dispositivo_temporal == dispositivo_destino:
        return
    raise PublicacionAtomicaNoDisponible(
        "PACKAGE_ATOMIC_PUBLISH_UNAVAILABLE: el temporal y el destino estan en volumenes "
        f"distintos ({dispositivo_temporal} y {dispositivo_destino}), asi que el rename no "
        "seria atomico. No se cae a copiar y borrar: eso publicaria un paquete a medias con "
        "la etiqueta de atomico puesta"
    )


@dataclass
class Publicacion:
    """El paquete mientras se escribe. `raiz` es el temporal, nunca el destino."""

    raiz: pathlib.Path
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    cameras: list[dict[str, Any]] = field(default_factory=list)
    manifest: dict[str, Any] = field(default_factory=dict)

    def anadir(self, ruta: str | pathlib.Path, **como: Any) -> dict[str, Any]:
        """Describe un artifact ya escrito y cerrado, leyendo sus bytes del disco."""
        entrada = describir_artifact(self.raiz, ruta, **como)
        self.artifacts.append(entrada)
        return entrada


@contextmanager
def publicar_paquete(
    destino: pathlib.Path,
    *,
    package_id: str,
    producer: str,
    version_del_productor: str = "0.1.0",
    temporal: pathlib.Path | None = None,
    dispositivo_temporal: int | None = None,
) -> Iterator[Publicacion]:
    """Abre una publicacion atomica: dentro se escriben los artifacts, al salir se sella.

    Si el bloque lanza, no se publica nada y el temporal se borra. El destino solo
    aparece cuando esta entero.
    """
    destino = pathlib.Path(destino)
    if destino.exists():
        raise ErrorDeSellado(
            f"{destino} ya existe y un paquete sellado no se reescribe: si esto es una version "
            "nueva, publicala con otra identidad — no se pisa 0004, se publica 0005"
        )

    padre = destino.parent
    padre.mkdir(parents=True, exist_ok=True)
    cuna = pathlib.Path(temporal) if temporal is not None else padre

    # Antes de escribir un solo byte. Si el temporal viene de fuera puede estar en
    # otro volumen, y entonces el rename final no seria atomico.
    comprobar_mismo_volumen(
        dispositivo_temporal=(
            dispositivo_temporal if dispositivo_temporal is not None else cuna.stat().st_dev
        ),
        dispositivo_destino=padre.stat().st_dev,
    )

    provisional = pathlib.Path(tempfile.mkdtemp(prefix=f".{destino.name}.", dir=cuna))
    obra = Publicacion(raiz=provisional)
    try:
        yield obra
        _sellar(obra, destino, package_id, producer, version_del_productor)
    except BaseException:
        shutil.rmtree(provisional, ignore_errors=True)
        raise


def _sellar(
    obra: Publicacion,
    destino: pathlib.Path,
    package_id: str,
    producer: str,
    version_del_productor: str,
) -> None:
    if not obra.artifacts:
        raise ErrorDeSellado("un paquete sin artifacts no declara nada; no se publica")

    manifest: dict[str, Any] = {
        **sobre_de(PAQUETE_DE_RECONSTRUCCION),
        "packageId": package_id,
        "state": "SEALED",
        "producer": {"name": producer, "version": version_del_productor},
        "artifacts": obra.artifacts,
        "scale": {"status": "RELATIVE", "source": "NONE"},
        "frameGraph": {"transforms": []},
        **obra.manifest,
    }
    if obra.cameras:
        manifest["cameras"] = obra.cameras

    # Todo lo que las decisiones exigen, comprobado sobre el paquete entero y
    # antes de que exista el destino: publicar mal es peor que no publicar.
    comprobar_rutas(obra.raiz, manifest["artifacts"])
    comprobar_integridad(obra.raiz, manifest["artifacts"])
    comprobar_camaras(manifest)
    comprobar_escala(manifest["scale"], manifest.get("budgets", []))
    comprobar_frame_graph(manifest["frameGraph"]["transforms"])

    # El manifest, el ultimo. Hasta aqui el temporal no tiene nada que nadie pueda
    # leer como un paquete.
    (obra.raiz / MANIFEST).write_text(volcar_documento(manifest) + "\n", encoding="utf-8")
    obra.raiz.rename(destino)
