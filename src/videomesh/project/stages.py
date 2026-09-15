"""El historial de ejecuciones del proyecto, en disco.

Se **añade**, no se reemplaza. Borrar el intento que falló es borrar la única
pista de por qué el siguiente se reejecutó, y esa pregunta aparece semanas después
cuando ya nadie se acuerda.
"""

import json
import pathlib
from typing import Any

from videomesh.contracts.serialization import volcar_json
from videomesh.domain.errores import ErrorDeProyecto
from videomesh.domain.stage import Determinismo, EjecucionDeStage, EstadoDeStage
from videomesh.project.store import MANIFIESTO

__all__ = ["HISTORIAL", "historial_de", "registrar_stage", "ultima_de"]

HISTORIAL = "stages.jsonl"


def _comprobar(proyecto: pathlib.Path) -> pathlib.Path:
    ruta = pathlib.Path(proyecto)
    if not (ruta / MANIFIESTO).is_file():
        raise ErrorDeProyecto(f"en {ruta} no hay ningun {MANIFIESTO}: no es un proyecto")
    return ruta


def registrar_stage(proyecto: pathlib.Path, ejecucion: EjecucionDeStage) -> None:
    """Añade una ejecución al historial. Una línea por ejecución, en orden."""
    ruta = _comprobar(proyecto)
    fila: dict[str, Any] = {
        "stage": ejecucion.stage,
        "estado": ejecucion.estado.value,
        "hash_de_entrada": ejecucion.hash_de_entrada,
        "hash_de_salida": ejecucion.hash_de_salida,
        "determinismo": ejecucion.determinismo.value,
        "proveedor": ejecucion.proveedor,
        "version_del_proveedor": ejecucion.version_del_proveedor,
        "duracion_s": ejecucion.duracion_s,
        "semilla": ejecucion.semilla,
    }
    with (ruta / HISTORIAL).open("a", encoding="utf-8") as fichero:
        fichero.write(volcar_json(fila) + "\n")


def historial_de(proyecto: pathlib.Path) -> list[EjecucionDeStage]:
    """Todas las ejecuciones registradas, en el orden en que pasaron."""
    ruta = _comprobar(proyecto)
    fichero = ruta / HISTORIAL
    if not fichero.is_file():
        return []
    ejecuciones = []
    for linea in fichero.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        fila = json.loads(linea)
        ejecuciones.append(
            EjecucionDeStage(
                stage=fila["stage"],
                estado=EstadoDeStage(fila["estado"]),
                hash_de_entrada=fila["hash_de_entrada"],
                hash_de_salida=fila["hash_de_salida"],
                determinismo=Determinismo(fila["determinismo"]),
                proveedor=fila["proveedor"],
                version_del_proveedor=fila["version_del_proveedor"],
                duracion_s=fila["duracion_s"],
                semilla=fila["semilla"],
            )
        )
    return ejecuciones


def ultima_de(proyecto: pathlib.Path, stage: str) -> EjecucionDeStage | None:
    """La última ejecución de ese stage, que es la que manda para decidir resume."""
    for ejecucion in reversed(historial_de(proyecto)):
        if ejecucion.stage == stage:
            return ejecucion
    return None
