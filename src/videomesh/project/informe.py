"""El informe de una etapa, en disco — el criterio de cierre del encargo 04.

> Una etapa que hace su trabajo y no dice cuanto cambio la superficie no esta
> hecha, esta a medias — y es la mitad que separa esto de cualquier otra
> herramienta.

Decimar es perder detalle, limpiar es tirar geometria, retopologizar es mover
vertices. Las tres son legitimas y las tres son **medibles**, asi que el informe
de cada etapa lleva: que parametros se usaron, que entro, que salio, y las
medidas —en su unidad y en las dos direcciones cuando son distancias de
superficie—. Lo que no se pudo medir se declara `NOT_RUN` con su motivo, en
`no_comprobado`, y nunca se calla.

Vive en `<proyecto>/etapas/<etapa>/`, junto a lo que la etapa produce: el informe
de una malla que no esta al lado no se puede revisar.
"""

import json
import pathlib
from typing import Any

from videomesh.contracts.estado import version_del_paquete
from videomesh.contracts.serialization import volcar_json
from videomesh.project.store import comprobar_proyecto

__all__ = [
    "ETAPAS",
    "INFORME",
    "TIPO_DE_DOCUMENTO",
    "directorio_de_etapa",
    "escribir_informe",
    "leer_informe",
]

#: Donde vive lo que produce cada etapa, dentro del proyecto.
ETAPAS = "etapas"

INFORME = "informe.json"

TIPO_DE_DOCUMENTO = "videomesh.stage-report"


def directorio_de_etapa(proyecto: pathlib.Path, etapa: str) -> pathlib.Path:
    """El directorio de trabajo de una etapa. Se crea al pedirlo: la etapa lo usa."""
    return comprobar_proyecto(proyecto) / ETAPAS / etapa


def escribir_informe(proyecto: pathlib.Path, etapa: str, documento: dict[str, Any]) -> pathlib.Path:
    """Escribe el informe de la etapa y devuelve su ruta.

    Lleva sobre como todo lo que este repositorio escribe (D16): un documento que
    no dice que es ni contra que contrato se escribio no se puede leer luego sin
    adivinar, y adivinar es lo que D14 prohibe.
    """
    destino = directorio_de_etapa(proyecto, etapa)
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / INFORME

    completo: dict[str, Any] = {
        "documentType": TIPO_DE_DOCUMENTO,
        "contractVersion": version_del_paquete(),
        "etapa": etapa,
        **documento,
    }
    ruta.write_text(volcar_json(completo) + "\n", encoding="utf-8")
    return ruta


def leer_informe(proyecto: pathlib.Path, etapa: str) -> dict[str, Any] | None:
    """El informe de esa etapa, o `None` si todavia no lo hay."""
    ruta = directorio_de_etapa(proyecto, etapa) / INFORME
    if not ruta.is_file():
        return None
    documento: dict[str, Any] = json.loads(ruta.read_text(encoding="utf-8"))
    return documento
