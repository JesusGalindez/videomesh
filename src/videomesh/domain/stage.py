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

from dataclasses import dataclass
from enum import Enum

__all__ = ["Determinismo", "EjecucionDeStage", "EstadoDeStage", "hay_que_reejecutar"]


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
