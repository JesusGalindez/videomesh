"""El proyecto: ciclo de vida pequeño y preparación derivada — §8 del roadmap.

El ciclo de vida se mantiene **deliberadamente pequeño**. No se duplica aquí la
máquina de estados de los stages: cada stage guarda su propia verdad, y un enum
global lineal que intentara resumirla mentiría en cuanto dos stages fueran por
caminos distintos.

La preparación —`readiness`— **se deriva** de los artifacts válidos que hay, y no
se asigna. Por eso no es un campo: un proyecto que se declarara listo a sí mismo
no estaría diciendo un estado sino una opinión, y nadie podría contradecirla.
"""

from dataclasses import dataclass, field
from enum import Enum

__all__ = ["CicloDeVida", "Preparacion", "Proyecto", "preparacion_de"]


class CicloDeVida(Enum):
    """Los cinco estados del proyecto entero. Ni uno más."""

    CREADO = "CREADO"
    ACTIVO = "ACTIVO"
    COMPLETADO = "COMPLETADO"
    FALLIDO = "FALLIDO"
    ARCHIVADO = "ARCHIVADO"


class Preparacion(Enum):
    """Para qué está listo el proyecto. Siempre derivado, nunca declarado."""

    MEDIA = "MEDIA_LISTA"
    DISPERSA = "DISPERSA_LISTA"
    DENSA = "DENSA_LISTA"
    RECONSTRUCCION = "RECONSTRUCCION_LISTA"
    PRODUCCION = "PRODUCCION_LISTA"


#: Qué artifact hace falta para cada preparación. Uno solo por ahora, y la lista
#: crece con las etapas; lo que no crece es la posibilidad de declararla a mano.
_LO_QUE_EXIGE = {
    Preparacion.MEDIA: "MEDIA",
    Preparacion.DISPERSA: "SPARSE",
    Preparacion.DENSA: "DENSE",
    Preparacion.RECONSTRUCCION: "MESH",
    Preparacion.PRODUCCION: "PRODUCTION",
}


@dataclass(frozen=True)
class Proyecto:
    """Un proyecto de VideoMesh, tal y como vive en `project.json`."""

    nombre: str
    estado: CicloDeVida = CicloDeVida.CREADO
    artifacts: tuple[str, ...] = field(default_factory=tuple)


def preparacion_de(proyecto: Proyecto) -> tuple[Preparacion, ...]:
    """Para qué está preparado, mirando lo que tiene."""
    tiene = set(proyecto.artifacts)
    return tuple(preparacion for preparacion, exigido in _LO_QUE_EXIGE.items() if exigido in tiene)
