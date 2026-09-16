"""Lo que comparten las etapas de acabado, escrito una sola vez.

Dos cosas, y las dos son de contabilidad y no de geometria:

`memoria_maxima_mb` — §9 pide medir el RSS en las etapas B y declararlo, «si hay
que trocear, que sea una decision tomada con un numero delante». `ru_maxrss` viene
en bytes en macOS y en kilobytes en Linux, que es la clase de diferencia que
produce un numero plausible y equivocado; por eso se convierte segun la plataforma
y no con una constante.

`medir_distancia` — la distancia contra la malla medida, o su `NOT_RUN` con el
motivo. Nunca una excepcion que pare la etapa: lo que no se pudo medir se declara
y se sigue, porque una etapa que no produce cuando no puede medir es peor que una
que produce y lo dice. Lo que si esta prohibido es callarse.
"""

import pathlib
import resource
import sys
from typing import Any

from videomesh.adapters import softsight
from videomesh.domain.errores import MedicionNoDisponible

__all__ = ["medir_distancia", "memoria_maxima_mb"]


def memoria_maxima_mb() -> float:
    """El pico de memoria residente de este proceso, en MB."""
    pico = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return pico / (1024 * 1024) if sys.platform == "darwin" else pico / 1024


def medir_distancia(
    referencia: pathlib.Path,
    salida: pathlib.Path,
    *,
    herramienta: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Las dos direcciones de la distancia, o `NOT_RUN` diciendo por que no hay."""
    try:
        return softsight.distancia_de_superficie(referencia, salida, herramienta=herramienta)
    except MedicionNoDisponible as fallo:
        return {"estado": "NOT_RUN", "motivo": str(fallo)}
