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
    "MALLA",
    "TIPO_DE_DOCUMENTO",
    "describir_malla",
    "directorio_de_etapa",
    "escribir_informe",
    "leer_informe",
    "malla_de_la_etapa",
    "salida_de",
]

#: Donde vive lo que produce cada etapa, dentro del proyecto.
ETAPAS = "etapas"

INFORME = "informe.json"

#: El nombre de la malla que produce una etapa. Uno, y en un solo sitio: la etapa
#: siguiente la busca por este nombre desde su propio directorio.
MALLA = "malla.ply"

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


def malla_de_la_etapa(proyecto: pathlib.Path, etapa: str) -> pathlib.Path:
    """Donde escribe su malla una etapa. No comprueba que exista: la va a escribir ella."""
    return directorio_de_etapa(proyecto, etapa) / MALLA


def describir_malla(ruta: pathlib.Path, *, identidad: str = "malla") -> dict[str, Any]:
    """Pesa y hashea una malla ya escrita, para que el informe pueda citarla.

    Se leen los bytes de disco y no se copia lo que alguien creia que pesaba, por
    lo mismo que en el paquete: el hash que una etapa publica es el de lo que hay.
    """
    import hashlib

    contenido = ruta.read_bytes()
    return {
        "id": identidad,
        "ruta": ruta.name,
        "bytes": len(contenido),
        "sha256": hashlib.sha256(contenido).hexdigest(),
    }


def salida_de(
    proyecto: pathlib.Path, etapa: str, *, identidad: str = "malla"
) -> dict[str, Any] | None:
    """Lo que esa etapa publico como su malla, leido de su informe.

    Es la entrada de la etapa siguiente, y se lee declarada en vez de rehashear el
    fichero: el hash ya lo calculo quien lo escribio, y volver a calcularlo daria
    dos cifras de lo mismo.
    """
    informe = leer_informe(proyecto, etapa)
    if informe is None:
        return None
    for salida in informe.get("salidas", []):
        if salida.get("id") == identidad:
            entrada: dict[str, Any] = salida
            return entrada
    return None
