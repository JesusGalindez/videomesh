"""La cadena de produccion: que etapa esta hecha, cual caduco y cual toca.

Empieza en el paquete que llega de Colab y sigue hacia el asset que se usa. Hoy
tiene una etapa registrada —`densa`— y crece con los bloques del encargo 04; lo
que **no** crece es la regla con la que se decide cada situacion:

```text
HECHA      hay una ejecucion acabada y su entrada es la de ahora
CADUCADA   hay una ejecucion acabada, pero su entrada ya no es la de ahora
TOCA       no hay ejecucion acabada, y sus entradas ya estan
ESPERA     sus entradas todavia no estan: la etapa anterior no ha acabado
```

Las etapas **caducan en silencio** —cambia el decimado y el mapa de normales que
se horneo contra la malla anterior ya no vale—, y lo que decide no es el estado
del registro sino el hash de su entrada. Un COMPLETE cuya entrada cambio no esta
hecho, esta caducado, y decirlo es el trabajo de este modulo.

No ejecuta nada. `estado_de_la_cadena` dice como esta la cadena; hacer algo con
eso es de quien llama, y en el encargo 04 eso es `videomesh next`.
"""

import pathlib
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from videomesh.application.densa import ETAPA as DENSA
from videomesh.application.densa import digest_de_entrada, manifest_de
from videomesh.domain.errores import ErrorDePaquete
from videomesh.domain.stage import EjecucionDeStage, EstadoDeStage
from videomesh.project.procedencia import ultima_de_la_etapa
from videomesh.project.stages import ultima_de

__all__ = ["CADENA", "Paso", "Situacion", "estado_de_la_cadena"]

#: Los estados en los que hay algo aprovechable. Los mismos que en `domain/stage.py`.
_ACABADOS = (EstadoDeStage.COMPLETE, EstadoDeStage.CACHED)


class Situacion(Enum):
    """La verdad de una etapa en la cadena, que no es su estado de ejecucion."""

    HECHA = "HECHA"
    CADUCADA = "CADUCADA"
    TOCA = "TOCA"
    ESPERA = "ESPERA"


@dataclass(frozen=True)
class Paso:
    """Una etapa y lo que se puede decir de ella ahora mismo."""

    etapa: str
    situacion: Situacion
    motivo: str


def _entrada_actual_de_densa(proyecto: pathlib.Path) -> str | None:
    """Lo que la etapa densa lee hoy: el paquete que se importo, tal y como esta.

    Se devuelve `None` cuando no se puede leer —no hay importacion o la fuente ya
    no esta—, y quien llama lo distingue de «la entrada cambio» porque son dos
    averias distintas.
    """
    anotada = ultima_de_la_etapa(proyecto, DENSA)
    if anotada is None:
        return None
    try:
        documento = manifest_de(pathlib.Path(anotada.fuente))
    except ErrorDePaquete:
        return None
    return digest_de_entrada(documento)


def _situacion(
    etapa: str,
    ultima: EjecucionDeStage | None,
    *,
    actual: str | None,
    motivo_sin_registro: str,
    motivo_sin_entrada: str,
) -> Paso:
    """La regla, escrita una sola vez para todas las etapas del encargo.

    Recibe la entrada de ahora ya resuelta —una cadena o `None`—, asi que cada
    etapa solo tiene que saber como se calcula la suya y no como se decide.
    """
    if ultima is None:
        return Paso(etapa, Situacion.TOCA, motivo_sin_registro)
    if ultima.estado not in _ACABADOS:
        return Paso(etapa, Situacion.TOCA, f"la ultima ejecucion quedo en {ultima.estado.value}")
    if actual is None:
        return Paso(etapa, Situacion.CADUCADA, motivo_sin_entrada)
    if ultima.hash_de_entrada != actual:
        return Paso(etapa, Situacion.CADUCADA, "la entrada es otra: lo que hay describe otra cosa")
    return Paso(etapa, Situacion.HECHA, "vigente")


def _paso_de_densa(proyecto: pathlib.Path) -> Paso:
    return _situacion(
        DENSA,
        ultima_de(proyecto, DENSA),
        actual=_entrada_actual_de_densa(proyecto),
        motivo_sin_registro="no hay ningun paquete importado todavia",
        motivo_sin_entrada="la procedencia o el paquete importado ya no estan donde estaban",
    )


#: El orden de la cadena. Ni alfabetico ni casual: `decimado` no puede ir antes
#: que `limpieza`, porque limpiar cambia lo que se decima.
CADENA: tuple[str, ...] = (DENSA,)

_PASOS: dict[str, Callable[[pathlib.Path], Paso]] = {DENSA: _paso_de_densa}


def estado_de_la_cadena(proyecto: pathlib.Path) -> tuple[Paso, ...]:
    """La cadena entera, etapa a etapa. No ejecuta nada."""
    return tuple(_PASOS[etapa](proyecto) for etapa in CADENA)
