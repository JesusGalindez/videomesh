"""Identidad del paquete e integridad de sus artifacts — V6, V8, D6 y D7.

Dos cosas que parecen de formato y son de identidad:

`packageId` **nunca se deduce del nombre del directorio**. El directorio es
comodidad humana; mover una carpeta no cambia la identidad de lo que hay dentro, y
si se infiriera, cambiarla la cambiaria.

`bytes` y `sha256` se leen **del fichero**, no se copian de lo que alguien creyo
que pesaba. `package-integrity-v1` tiene los casos del lado que los rechaza; aqui
hay que producirlos, que es mas exigente que no fallarlos.

Los identificadores `SS-PKG-*` no aparecen aqui. Juzgar es del consumidor: este
lado escribe, y se niega a escribir mal.
"""

import hashlib
import pathlib
from collections.abc import Mapping, Sequence
from typing import Any

__all__ = [
    "ErrorDeIntegridad",
    "ErrorDeRuta",
    "comprobar_integridad",
    "comprobar_rutas",
    "describir_artifact",
    "identidad_de",
]

#: Solo una malla de triangulos habla de superficie, asi que solo ella declara
#: de donde viene esa superficie (D21).
_CON_SUPERFICIE = "TRIANGLE_MESH"

_HEXADECIMAL = set("0123456789abcdef")


class ErrorDeIntegridad(ValueError):
    """Lo que el manifest dice de un artifact no es lo que el artifact es."""


class ErrorDeRuta(ValueError):
    """Un artifact no resuelve dentro del paquete, o no resuelve."""


def identidad_de(manifest: Mapping[str, Any], raiz: pathlib.Path) -> str:
    """Devuelve `packageId`. Nunca lo completa con el nombre del directorio.

    La raiz se recibe para dejar claro que **no se usa**: es donde la tentacion
    esta, y un valor por defecto sacado de ahi seria indistinguible de uno
    declarado hasta el dia en que alguien renombra la carpeta.
    """
    del raiz
    identidad = manifest.get("packageId")
    if not identidad:
        raise ErrorDeIntegridad(
            "el manifest no declara packageId, y no se deduce del nombre del directorio: "
            "el nombre es comodidad humana y la identidad tiene que sobrevivir a moverlo"
        )
    return str(identidad)


def describir_artifact(
    raiz: pathlib.Path,
    ruta: str | pathlib.Path,
    *,
    identidad: str,
    tipo: str,
    purely_reconstructed: bool | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Lee el fichero y devuelve su entrada del manifest, con `bytes` y `sha256`."""
    relativa = pathlib.PurePosixPath(pathlib.PurePath(ruta).as_posix())
    fichero = raiz / relativa
    if not fichero.is_file():
        raise ErrorDeRuta(f"el artifact {identidad!r} apunta a {relativa}, que no existe")

    contenido = fichero.read_bytes()
    entrada: dict[str, Any] = {
        "id": identidad,
        "type": tipo,
        "path": str(relativa),
        "bytes": len(contenido),
        "sha256": hashlib.sha256(contenido).hexdigest(),
    }

    if tipo == _CON_SUPERFICIE:
        if purely_reconstructed is None:
            raise ErrorDeIntegridad(
                f"{identidad!r} es una malla y no declara purelyReconstructed; es requerida, "
                "y cuando no se puede demostrar `true` se emite `false` (D21)"
            )
        entrada["purelyReconstructed"] = purely_reconstructed
    elif purely_reconstructed is not None:
        raise ErrorDeIntegridad(
            f"{identidad!r} es {tipo} y declara purelyReconstructed, que ahi esta prohibida: "
            "no tiene superficie de la que hablar (D21)"
        )

    entrada.update(extra)
    return entrada


def comprobar_rutas(raiz: pathlib.Path, artifacts: Sequence[Mapping[str, Any]]) -> None:
    """Todo artifact resuelve dentro de la raiz del paquete (D6).

    La ruta se juzga **por lo que dice antes de tocar el disco** —absoluta o con
    `..` se rechaza aunque apunte dentro— y solo despues por donde resuelve. Una
    regla que depende de a donde apunte hoy cambia de resultado manana.
    """
    raiz_real = raiz.resolve()
    vistos: set[str] = set()

    for artifact in artifacts:
        identidad = artifact["id"]
        if identidad in vistos:
            raise ErrorDeRuta(f"el artifact {identidad!r} esta declarado dos veces")
        vistos.add(identidad)

        declarada = str(artifact["path"])
        ruta = pathlib.PurePosixPath(declarada)
        if ruta.is_absolute() or pathlib.PurePath(declarada).is_absolute():
            raise ErrorDeRuta(f"{identidad!r} declara una ruta absoluta: {declarada}")
        if ".." in ruta.parts:
            raise ErrorDeRuta(f"{identidad!r} declara una ruta con `..`: {declarada}")

        destino = raiz / declarada
        if not destino.exists():
            raise ErrorDeRuta(f"el artifact {identidad!r} apunta a {declarada}, que no existe")
        # `resolve` sigue los enlaces: es lo unico que caza un escape cuyo destino
        # tiene el mismo tamano y el mismo hash, y solo se distingue por donde vive.
        real = destino.resolve()
        if not real.is_relative_to(raiz_real):
            raise ErrorDeRuta(
                f"{identidad!r} declara {declarada}, que resuelve fuera de la raiz del paquete: "
                f"{real}"
            )


def comprobar_integridad(raiz: pathlib.Path, artifacts: Sequence[Mapping[str, Any]]) -> None:
    """`bytes` y `sha256` declarados son los del fichero que hay en disco."""
    for artifact in artifacts:
        identidad = artifact["id"]
        declarado = str(artifact["sha256"])
        if len(declarado) != 64 or not set(declarado) <= _HEXADECIMAL:
            raise ErrorDeIntegridad(
                f"el sha256 de {identidad!r} no esta en hexadecimal minuscula de 64 caracteres: "
                f"{declarado!r}. Esto lo arregla quien escribe el manifest, no el contenido"
            )

        contenido = (raiz / str(artifact["path"])).read_bytes()
        if artifact["bytes"] != len(contenido):
            raise ErrorDeIntegridad(
                f"{identidad!r} declara {artifact['bytes']} bytes y el fichero tiene "
                f"{len(contenido)}"
            )
        real = hashlib.sha256(contenido).hexdigest()
        if declarado != real:
            raise ErrorDeIntegridad(
                f"el sha256 de {identidad!r} no cuadra con su contenido: declarado "
                f"{declarado[:8]}..., real {real[:8]}..."
            )
