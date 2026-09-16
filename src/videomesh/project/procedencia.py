"""La procedencia del proyecto, en disco — §10 del roadmap.

Un fichero JSONL al lado del historial de stages, y por la misma razon: **se
anade, no se reemplaza**. Borrar la procedencia de la densa que se descarto es
borrar la unica pista de con que se comparaba la que se quedo.

Las dos cosas que este fichero existe para no perder: de que maquina salio y con
que version. Dos densas del mismo objeto hechas con dos versiones de COLMAP no son
comparables, y dentro de seis meses nadie se acordara de cual era cual.
"""

import json
import pathlib
from typing import Any

from videomesh.contracts.serialization import volcar_json
from videomesh.domain.procedencia import EstadoDeProcedencia, Procedencia
from videomesh.project.store import comprobar_proyecto

__all__ = ["PROCEDENCIA", "anotar_procedencia", "procedencia_de"]

PROCEDENCIA = "procedencia.jsonl"


def anotar_procedencia(proyecto: pathlib.Path, procedencia: Procedencia) -> None:
    """Anade una linea al registro. Una por artifact y etapa."""
    ruta = comprobar_proyecto(proyecto)
    fila: dict[str, Any] = {
        "etapa": procedencia.etapa,
        "artefacto": procedencia.artefacto,
        "estado": procedencia.estado.value,
        "productor": procedencia.productor,
        "version_del_productor": procedencia.version_del_productor,
        "package_id": procedencia.package_id,
        "fuente": procedencia.fuente,
        "ruta_del_artefacto": procedencia.ruta_del_artefacto,
        "sha256_del_artefacto": procedencia.sha256_del_artefacto,
        "maquina": procedencia.maquina,
    }
    with (ruta / PROCEDENCIA).open("a", encoding="utf-8") as fichero:
        fichero.write(volcar_json(fila) + "\n")


def procedencia_de(proyecto: pathlib.Path) -> list[Procedencia]:
    """Todo lo anotado, en el orden en que paso."""
    ruta = comprobar_proyecto(proyecto)
    fichero = ruta / PROCEDENCIA
    if not fichero.is_file():
        return []

    anotadas = []
    for linea in fichero.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        fila = json.loads(linea)
        anotadas.append(
            Procedencia(
                etapa=fila["etapa"],
                artefacto=fila["artefacto"],
                estado=EstadoDeProcedencia(fila["estado"]),
                productor=fila["productor"],
                version_del_productor=fila["version_del_productor"],
                package_id=fila["package_id"],
                fuente=fila["fuente"],
                ruta_del_artefacto=fila["ruta_del_artefacto"],
                sha256_del_artefacto=fila["sha256_del_artefacto"],
                maquina=fila["maquina"],
            )
        )
    return anotadas


def ultima_de_la_etapa(proyecto: pathlib.Path, etapa: str) -> Procedencia | None:
    """La ultima procedencia anotada por esa etapa, que es la que describe lo de ahora."""
    for anotada in reversed(procedencia_de(proyecto)):
        if anotada.etapa == etapa:
            return anotada
    return None
