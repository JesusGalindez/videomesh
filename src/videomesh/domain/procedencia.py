"""La procedencia de un artifact, en grueso — §10 del roadmap.

Nueve estados generales, y una regla congelada que no se negocia:

```text
RECONSTRUCTED != INFERRED
```

V1 usa procedencia **a nivel de artifact**, no por region ni por triangulo, y con
eso basta para lo que este repositorio tiene que poder afirmar: que una superficie
vino de evidencia y no de una estimacion. D21 anade la garantia especifica de
elegibilidad —`purelyReconstructed`—, que responde a la misma pregunta con mas
detalle.

`maquina` es lo unico de este registro que no vive en el paquete. El esquema de
SoftSight no tiene campo para ella y no se le anade uno desde aqui: se recoge al
importar, que es el unico momento en que alguien lo sabe. Y `None` no es un hueco
—significa que la etapa corrio en esta maquina, que no viaja—, que es distinto de
no declararla.
"""

from dataclasses import dataclass
from enum import Enum

__all__ = ["EstadoDeProcedencia", "Procedencia"]


class EstadoDeProcedencia(Enum):
    """§10, los nueve. Ni uno mas, porque uno de mas invita a elegir el comodo."""

    CAPTURADO = "CAPTURED"
    DERIVADO = "DERIVED"
    RECONSTRUIDO = "RECONSTRUCTED"
    REPARADO = "REPAIRED"
    SIMPLIFICADO = "SIMPLIFIED"
    HORNEADO = "BAKED"
    INFERIDO = "INFERRED"
    GENERADO = "GENERATED"
    AUTORADO = "AUTHORED"


@dataclass(frozen=True)
class Procedencia:
    """De donde sale un artifact: que etapa, con que estado y con que productor."""

    etapa: str
    artefacto: str
    estado: EstadoDeProcedencia
    productor: str
    version_del_productor: str
    #: `None` cuando el artifact no viene de un paquete sellado de fuera sino de una
    #: etapa de aqui. No es un hueco: el nombre de la etapa ya dice quien lo hizo, y
    #: rellenarlo con el nombre del proyecto seria un dato inventado.
    package_id: str | None
    fuente: str
    ruta_del_artefacto: str
    sha256_del_artefacto: str
    maquina: str | None = None
