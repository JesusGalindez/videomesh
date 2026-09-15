"""Serializacion JSON estricta — V1, V2 y D17.

Toda escritura JSON de este repositorio pasa por aqui. `json.dumps` con los
valores por omision emite `NaN` e `Infinity`, que **no son JSON**: el consumidor
los rechaza, y el que sobreviva se convierte en una medida que nadie puede
interpretar. D17 obliga a rechazarlos en origen, sin confiar en que los cace Node.

`allow_nan=False` solo no basta para dar un mensaje util: dice que hay un no
finito, no donde esta. En una matriz de dieciseis numeros eso son dieciseis
sitios donde mirar, asi que el documento se recorre antes y el error nombra la
ruta exacta.
"""

import json
import math
from typing import Any

__all__ = ["ErrorNumeroNoFinito", "volcar_json"]


class ErrorNumeroNoFinito(ValueError):
    """Un `NaN` o un infinito llego a la serializacion. Nunca sale del proceso."""


def _nombre(valor: float) -> str:
    if math.isnan(valor):
        return "NaN"
    return "Infinity" if valor > 0 else "-Infinity"


def _comprobar(valor: Any, ruta: str) -> None:
    """Recorre el documento y falla en el primer no finito, nombrando su ruta."""
    if isinstance(valor, float) and not math.isfinite(valor):
        donde = ruta or "la raiz"
        raise ErrorNumeroNoFinito(f"{donde} es {_nombre(valor)} y tiene que ser un numero finito")
    if isinstance(valor, dict):
        for clave, hijo in valor.items():
            _comprobar(clave, f"{ruta}.<clave>" if ruta else "<clave>")
            _comprobar(hijo, f"{ruta}.{clave}" if ruta else str(clave))
    elif isinstance(valor, (list, tuple)):
        for indice, hijo in enumerate(valor):
            _comprobar(hijo, f"{ruta}[{indice}]")


def volcar_json(documento: Any) -> str:
    """Devuelve el JSON canonico del documento, o falla si contiene un no finito.

    Canonico quiere decir claves ordenadas y sin espacios: dos generaciones del
    mismo contenido dan los mismos bytes, que es lo que `expected.json` necesita
    para ser determinista (V4).
    """
    _comprobar(documento, "")
    return json.dumps(documento, allow_nan=False, sort_keys=True, separators=(",", ":"))
