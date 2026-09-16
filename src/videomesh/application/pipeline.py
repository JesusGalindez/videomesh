"""Los cuatro stages del pipeline — §11 y §20 del roadmap.

```text
analyze     video    -> frames y metadatos        FFmpeg
build       frames   -> reconstruccion dispersa   COLMAP
reconstruct dispersa -> malla                     COLMAP
produce     malla    -> paquete sellado           videomesh
```

**Hoy solo el último puede trabajar.** FFmpeg y COLMAP no están en esta máquina,
así que los otros tres fallan con `ProveedorNoDisponible` diciendo qué falta, para
qué y cómo se instala. Que existan y fallen bien no es lo mismo que que no
existan: un comando ausente le dice al usuario que se equivocó de nombre.

Lo que decide si un stage se ejecuta **no es su estado, son sus hashes** (§11). Un
`COMPLETE` cuya entrada cambió no está hecho, está caducado, y reutilizarlo
produciría una salida que describe otra cosa.
"""

import hashlib
import importlib.metadata
import json
import pathlib
import time

from videomesh.application.cube_v1 import generar_cube_v1
from videomesh.domain.project import CicloDeVida, Proyecto
from videomesh.domain.stage import Determinismo, EjecucionDeStage, EstadoDeStage, hay_que_reejecutar
from videomesh.project.package import identidad_de
from videomesh.project.stages import registrar_stage, ultima_de
from videomesh.project.store import abrir_proyecto, guardar_proyecto
from videomesh.providers.externos import COLMAP, FFMPEG, Externo, exigir

__all__ = ["PAQUETES", "STAGES", "ejecutar_stage", "hash_de_entrada"]

#: En el orden del pipeline, que no es alfabético ni casual: `produce` no puede
#: ir antes que `reconstruct`.
STAGES = ("analyze", "build", "reconstruct", "produce")

#: Dónde viven los paquetes dentro del proyecto.
PAQUETES = "paquetes"

#: Qué binario de fuera necesita cada stage. `produce` no está: escribe JSON,
#: hashes y PLY, y eso lo hace este repositorio entero.
_EXIGE: dict[str, Externo] = {
    "analyze": FFMPEG,
    "build": COLMAP,
    "reconstruct": COLMAP,
}


def hash_de_entrada(proyecto: pathlib.Path) -> str:
    """Lo que el stage **lee**, resumido. Ni un byte más.

    La primera versión hasheaba `project.json` entero, y estaba mal de una forma
    que conviene dejar escrita: `produce` **escribe** en ese fichero al acabar
    —añade el artifact y pasa el proyecto a ACTIVO—, así que su propia salida
    cambiaba su hash de entrada y el stage se invalidaba a sí mismo. Nunca podía
    dar `CACHED`, y el segundo intento moría contra el paquete ya sellado.

    Lo que de verdad decide la salida de `produce` hoy es quién la genera: la
    geometría del cubo es fija y el generador es determinista. El día que
    `reconstruct` produzca una malla, esa malla entra aquí — y seguirá sin entrar
    la contabilidad que el propio stage escribe.
    """
    proyecto_leido = abrir_proyecto(proyecto)
    materia = f"{proyecto_leido.nombre}\ncube-v1\n{_version_de_videomesh()}"
    return hashlib.sha256(materia.encode("utf-8")).hexdigest()


def _version_de_videomesh() -> str:
    try:
        return importlib.metadata.version("videomesh")
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover - solo sin instalar
        return "desconocida"


def _produce(proyecto: pathlib.Path) -> tuple[pathlib.Path, str]:
    """Fabrica el paquete y lo sella. Devuelve el manifest y el `packageId`.

    El cubo es la única fuente de malla que hay hoy, y es de verdad: el mismo
    paquete que el consumidor de SoftSight certifica COMPLETE + PASS. Cuando
    `reconstruct` exista, la malla vendrá de él y esto no cambiará de forma.
    """
    destino = proyecto / PAQUETES / "cube-v1"
    generar_cube_v1(destino)
    manifest = destino / "manifest.json"
    documento = json.loads(manifest.read_text(encoding="utf-8"))
    return manifest, identidad_de(documento, destino)


def ejecutar_stage(proyecto: pathlib.Path, stage: str) -> pathlib.Path:
    """Ejecuta un stage y registra lo que hizo. Devuelve lo que produjo.

    Si la entrada no cambió y el stage es reproducible, no se rehace: se registra
    `CACHED` y se devuelve lo de antes. El registro se escribe igual, porque una
    ejecución que no deja rastro no se puede reanudar ni auditar.
    """
    if stage not in STAGES:
        raise ValueError(f"no existe el stage {stage!r}; los que hay son: {', '.join(STAGES)}")

    abrir_proyecto(proyecto)  # que sea un proyecto, y no un directorio cualquiera

    externo = _EXIGE.get(stage)
    if externo is not None:
        # Antes de tocar nada: §21 dice que una incompatibilidad conocida falla
        # pronto, y esta es la más conocida de todas.
        exigir(externo)
        raise AssertionError(f"{stage}: el binario esta y el adaptador no")  # pragma: no cover

    entrada = hash_de_entrada(proyecto)
    ultima = ultima_de(proyecto, stage)
    if not hay_que_reejecutar(ultima, hash_de_entrada=entrada):
        assert ultima is not None and ultima.hash_de_salida is not None
        registrar_stage(
            proyecto,
            EjecucionDeStage(
                stage=stage,
                estado=EstadoDeStage.CACHED,
                hash_de_entrada=entrada,
                hash_de_salida=ultima.hash_de_salida,
                determinismo=Determinismo.DETERMINISTA,
                proveedor="videomesh/cube-v1",
                version_del_proveedor=_version_de_videomesh(),
                duracion_s=0.0,
            ),
        )
        return proyecto / PAQUETES / "cube-v1" / "manifest.json"

    empezado = time.monotonic()
    manifest, package_id = _produce(proyecto)
    registrar_stage(
        proyecto,
        EjecucionDeStage(
            stage=stage,
            estado=EstadoDeStage.COMPLETE,
            hash_de_entrada=entrada,
            hash_de_salida=package_id,
            determinismo=Determinismo.DETERMINISTA,
            proveedor="videomesh/cube-v1",
            version_del_proveedor=_version_de_videomesh(),
            duracion_s=time.monotonic() - empezado,
        ),
    )

    proyecto_leido = abrir_proyecto(proyecto)
    artifacts = tuple(dict.fromkeys([*proyecto_leido.artifacts, "MESH"]))
    guardar_proyecto(
        proyecto,
        Proyecto(
            nombre=proyecto_leido.nombre,
            estado=CicloDeVida.ACTIVO,
            artifacts=artifacts,
        ),
    )
    return manifest
