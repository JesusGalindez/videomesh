"""VideoMesh actúa por el identificador del aviso, nunca por su mensaje — D2.

    code     SS-PKG-001              identificador neutro; esto es lo que se parsea
    reason   RUTA_FUERA_DE_LA_RAIZ   motivo canonico, vocabulario del contrato
    message  texto en español con la ruta concreta; **nunca se parsea**

La regla se ganó su prueba sola: el 2026-09-13 el idioma de los mensajes pasó a
español entero, los treinta y seis textos con él, y no rompió a nadie porque lo
que se parsea es el identificador. Un `SS-CAM-001` sigue siendo `SS-CAM-001`.

Un motivo puede repetirse y un identificador no. `SS-PKG-001` y `SS-PKG-003`
comparten `RUTA_FUERA_DE_LA_RAIZ` porque el resultado es el mismo y la causa no
—una ruta con `..` y un enlace que escapa—, asi que agrupar por motivo pierde
justo la diferencia que hay que arreglar.

Aquí **no vive la tabla de identificadores**. La tabla es de SoftSight, que es
quien los emite; duplicarla aqui seria un segundo original que diverge en el
primer codigo nuevo. Lo que vive aqui es la forma y los espacios, que son lo que
el contrato fija.
"""

import re
from collections.abc import Mapping, Sequence
from typing import Any

__all__ = ["ESPACIOS", "avisos_de", "es_identificador", "espacio_de", "veredicto_de"]

#: Los doce espacios que D2 declara. Uno que no esté aqui es contrato nuevo, y no
#: se interpreta por parecido: `SS-MESH-001` no es «algo de geometria».
ESPACIOS = (
    "SS-PKG",
    "SS-IO",
    "SS-GEO",
    "SS-RECON",
    "SS-CAM",
    "SS-COV",
    "SS-CONF",
    "SS-PROD",
    "SS-LOD",
    "SS-UV",
    "SS-PBR",
    "SS-COLL",
)

_FORMA = re.compile(r"^(" + "|".join(ESPACIOS) + r")-(\d{3})$")


def es_identificador(texto: str) -> bool:
    """Si el texto es un identificador entero y de un espacio declarado."""
    return bool(_FORMA.match(texto))


def espacio_de(identificador: str) -> str:
    """El espacio al que pertenece un identificador."""
    encontrado = _FORMA.match(identificador)
    if encontrado is None:
        raise ValueError(f"{identificador!r} no es un identificador de la frontera")
    return encontrado.group(1)


def avisos_de(informe: Mapping[str, Any]) -> list[str]:
    """Los identificadores de los avisos del informe, en el orden en que vienen.

    Un aviso sin identificador o de un espacio desconocido **no se ignora**: si se
    tragara en silencio, el dia que el otro lado añada un espacio VideoMesh
    seguiria diciendo que todo va bien.
    """
    identificadores: list[str] = []
    avisos: Sequence[Mapping[str, Any]] = informe.get("warnings", [])
    for aviso in avisos:
        identificador = aviso.get("code")
        if not identificador:
            raise ValueError(
                "el informe trae un aviso sin identificador; el mensaje no se parsea, "
                "asi que sin `code` no hay nada que interpretar"
            )
        if not es_identificador(identificador):
            raise ValueError(
                f"{identificador} no pertenece a ningun espacio declarado en D2; "
                "un espacio nuevo es contrato nuevo y no se interpreta por parecido"
            )
        identificadores.append(str(identificador))
    return identificadores


def veredicto_de(informe: Mapping[str, Any]) -> tuple[str, str]:
    """Los **dos** ejes del veredicto: ejecución y certificación (D3).

    Se devuelven juntos y sin colapsar. `INCONCLUSIVE` no es `PASS`: quiere decir
    que faltaba evidencia o que no habia nada que medir, y tratarlo como aprobado
    convierte «no se pudo mirar» en «esta bien».
    """
    return str(informe["execution"]), str(informe["certification"])
