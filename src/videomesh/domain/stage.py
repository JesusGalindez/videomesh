"""El stage y su verdad de ejecución — §11 del roadmap.

Cada stage guarda lo que hizo: estado, hashes de entrada y de salida,
determinismo, proveedor con su versión y duración. No hay un enum global que lo
resuma, porque en cuanto dos stages van por caminos distintos ese resumen miente.

**Lo que decide si un stage se puede saltar no es su estado: son sus hashes.** Un
COMPLETE cuya entrada cambió no está hecho, está caducado, y reutilizarlo produce
una salida que describe otra cosa. `COMPLETE` dice que salió bien; el
determinismo dice si volvería a salir igual, y solo lo segundo justifica saltarse
el trabajo.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

__all__ = [
    "Determinismo",
    "EjecucionDeStage",
    "EstadoDeStage",
    "hay_que_reejecutar",
    "hash_de_entrada",
]


class EstadoDeStage(Enum):
    """La verdad de ejecución de un stage, suya y de nadie más."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CACHED = "CACHED"


class Determinismo(Enum):
    """Si la misma entrada volvería a dar la misma salida.

    No se confunde con `MeasurementClass` ni con `ReproducibilityMode`, que son de
    métricas y responden a otra pregunta: aquéllas dicen cómo se midió algo, ésta
    dice si se puede no volver a hacerlo.
    """

    DETERMINISTA = "DETERMINISTIC"
    DETERMINISTA_CON_SEMILLA = "DETERMINISTIC_WITH_SEED"
    MEJOR_ESFUERZO = "BEST_EFFORT"
    NO_DETERMINISTA = "NON_DETERMINISTIC_PROVIDER"


#: Los dos estados en los que hay algo aprovechable. `SKIPPED` no entra: saltarse
#: un stage no produce salida, asi que no hay nada que reutilizar.
_ACABADOS = (EstadoDeStage.COMPLETE, EstadoDeStage.CACHED)

#: Los determinismos que permiten reutilizar la salida sin volver a medir.
_REPRODUCIBLES = (Determinismo.DETERMINISTA, Determinismo.DETERMINISTA_CON_SEMILLA)


@dataclass(frozen=True)
class EjecucionDeStage:
    """Lo que un stage dejó registrado al pasar."""

    stage: str
    estado: EstadoDeStage
    hash_de_entrada: str
    determinismo: Determinismo
    proveedor: str
    version_del_proveedor: str
    duracion_s: float
    hash_de_salida: str | None = None
    semilla: int | None = None

    def __post_init__(self) -> None:
        if self.estado in _ACABADOS and not self.hash_de_salida:
            raise ValueError(
                f"{self.stage} dice {self.estado.value} y no declara hash_de_salida: "
                "un stage acabado que no dice que produjo no se puede comprobar ni reutilizar"
            )
        if self.duracion_s < 0:
            raise ValueError(f"{self.stage} declara una duracion negativa: {self.duracion_s}")


def hash_de_entrada(
    *,
    entradas: Sequence[str],
    parametros: Mapping[str, Any],
    proveedor: str,
    version_del_proveedor: str,
) -> str:
    """El resumen de lo que un stage lee, con lo que lo lee y con que version.

    Tres cosas entran, y las tres cambian la salida, asi que las tres tienen que
    cambiar el hash:

    - **lo que lee**: los hashes de sus entradas, en orden. Cambiar la malla de
      arriba tiene que caducar lo de abajo (§9).
    - **con que parametros**: decimar a otro objetivo es otro trabajo, no el
      mismo con otra etiqueta.
    - **con que proveedor y version**: §9 lo dice con todas las letras —los
      proveedores cambian resultados entre versiones— y una version nueva deja el
      registro describiendo una salida que ya no se produciria igual.

    Se resume texto canonico y no `repr` de un diccionario: el orden de las claves
    no puede depender de por donde se itero.
    """
    texto = json.dumps(
        {
            "entradas": list(entradas),
            "parametros": {clave: parametros[clave] for clave in sorted(parametros)},
            "proveedor": f"{proveedor} {version_del_proveedor}",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def hay_que_reejecutar(
    ultima: EjecucionDeStage | None,
    *,
    hash_de_entrada: str,
    semilla: int | None = None,
) -> bool:
    """Si el stage hay que volver a ejecutarlo, y no si «está hecho».

    Cuatro motivos, y ninguno es el estado por sí solo:

    - no hay ejecución previa
    - la anterior no llegó a acabar —`RUNNING` incluido: un proceso muerto deja el
      stage ahí para siempre—
    - la entrada es otra
    - la salida no se puede reproducir, asi que reutilizarla afirmaria algo que no
      se sabe
    """
    if ultima is None:
        return True
    if ultima.estado not in _ACABADOS:
        return True
    if ultima.hash_de_entrada != hash_de_entrada:
        return True
    if ultima.determinismo not in _REPRODUCIBLES:
        return True
    return (
        ultima.determinismo is Determinismo.DETERMINISTA_CON_SEMILLA and ultima.semilla != semilla
    )
