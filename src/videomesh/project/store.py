"""El proyecto en disco: `project.json` con su sobre.

Se escribe con el mismo serializador estricto que todo lo demás, y con sobre: un
documento que no dice qué es no se puede leer luego sin adivinar, y adivinar es lo
que D14 prohíbe con los nombres sueltos.
"""

import json
import pathlib
from typing import Any

from videomesh.contracts.estado import version_del_paquete
from videomesh.contracts.serialization import volcar_json
from videomesh.domain.errores import ErrorDeProyecto
from videomesh.domain.project import CicloDeVida, Proyecto

__all__ = [
    "MANIFIESTO",
    "TIPO_DE_DOCUMENTO",
    "abrir_proyecto",
    "crear_proyecto",
    "guardar_proyecto",
]

MANIFIESTO = "project.json"
TIPO_DE_DOCUMENTO = "videomesh.project"


def crear_proyecto(ruta: pathlib.Path, *, nombre: str) -> Proyecto:
    """Crea el directorio y escribe su manifiesto. No pisa lo que ya hubiera."""
    ruta = pathlib.Path(ruta)
    if (ruta / MANIFIESTO).exists():
        raise ErrorDeProyecto(
            f"{ruta} ya existe como proyecto: pisarlo seria perder su historia. "
            "Si quieres empezar de cero, muevelo o usa otro directorio"
        )
    ruta.mkdir(parents=True, exist_ok=True)
    proyecto = Proyecto(nombre=nombre, estado=CicloDeVida.CREADO)
    guardar_proyecto(ruta, proyecto)
    return proyecto


def guardar_proyecto(ruta: pathlib.Path, proyecto: Proyecto) -> None:
    """Escribe el manifiesto del proyecto."""
    documento = {
        "documentType": TIPO_DE_DOCUMENTO,
        "contractVersion": version_del_paquete(),
        "nombre": proyecto.nombre,
        "estado": proyecto.estado.value,
        "artifacts": list(proyecto.artifacts),
    }
    (pathlib.Path(ruta) / MANIFIESTO).write_text(volcar_json(documento) + "\n", encoding="utf-8")


def abrir_proyecto(ruta: pathlib.Path) -> Proyecto:
    """Lee el proyecto de disco, o dice por qué no puede."""
    manifiesto = pathlib.Path(ruta) / MANIFIESTO
    if not manifiesto.is_file():
        raise ErrorDeProyecto(f"en {ruta} no hay ningun {MANIFIESTO}: no es un proyecto")

    crudo: dict[str, Any] = json.loads(manifiesto.read_text(encoding="utf-8"))
    tipo = crudo.get("documentType")
    if tipo != TIPO_DE_DOCUMENTO:
        raise ErrorDeProyecto(
            f"{manifiesto} declara documentType {tipo!r} y no {TIPO_DE_DOCUMENTO!r}; "
            "un manifest de otra cosa en la carpeta no la convierte en proyecto"
        )
    return Proyecto(
        nombre=crudo["nombre"],
        estado=CicloDeVida(crudo["estado"]),
        artifacts=tuple(crudo.get("artifacts", [])),
    )
