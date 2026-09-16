"""La etapa `textura`, declarada **sin instrumento** — encargo 04, D1.

La etapa la pide el encargo con **OpenMVS `TextureMesh`**: proyecta los fotogramas
reales sobre la malla y devuelve el color del objeto con lo que solo tienen las
imagenes —el desgaste, las manchas, la luz vista por cada camara—. El instrumento
no esta en esta maquina y no se puede poner: no esta en PyPI, y no hay brew ni cmake
para construirlo (comprobado el 2026-09-16).

Lo que **si** hay al lado, y no se usa, conviene dejarlo escrito antes de que a
alguien le tiente:

```text
hornear los colores de la nube dispersa sobre el atlas   pymeshlab lo sabe hacer
```

Pero lo que se interpola desde la nube **no es el color que vio ninguna camara**: es
la mezcla de la luz de todas, sin ninguna correspondencia texel-fotograma que
auditar. La razon de ser de D1 es esa correspondencia, y una textura que nadie
fotografio **parece** la etapa hecha. Por lo mismo que en la retopologia: una etapa
que no dice lo que es es peor que una declarada sin instrumento.

Asi que esta etapa no se implementa: se declara. `exigir` es su frontera, con las
tres partes del mensaje que pide `providers/externos.py`, y `motivo_de_ausencia` es
lo que `status` publica para que nadie tenga que lanzarla para enterarse.
"""

import shutil

from videomesh.domain.errores import ProveedorNoDisponible

__all__ = [
    "ETAPA",
    "INSTALACION",
    "PROVEEDOR",
    "exigir",
    "instalado",
    "motivo_de_ausencia",
]

ETAPA = "textura"

PROVEEDOR = "openmvs-texturemesh"

#: Los nombres con los que puede estar en el PATH. OpenMVS instala el binario como
#: `TextureMesh` junto al resto de sus herramientas.
ORDENES = ("TextureMesh", "texturemesh", "TextureMeshCLI")

INSTALACION = (
    "se construye desde fuente (OpenMVS, C++ con CMake y Eigen) o por gestor de "
    "paquetes donde exista. Esta maquina no tiene brew ni cmake, asi que el primer "
    "paso es poner un sistema de construccion"
)

#: Por que no se sustituye, en una linea, para que viaje al informe y a `status`.
_NO_SE_SUSTITUYE = (
    "no se sustituye hornenando colores de la nube: lo interpolado desde la nube no "
    "es el color que vio ninguna cámara, y sin la correspondencia texel-fotograma no "
    "hay etapa D1 que auditar"
)


def instalado() -> bool:
    """Si el TextureMesh de OpenMVS esta en el PATH."""
    return any(shutil.which(orden) is not None for orden in ORDENES)


def motivo_de_ausencia() -> str | None:
    """Por que esta etapa no se puede hacer ahora, o `None` si si se puede.

    Lo lee `status` para publicarlo **sin lanzar la etapa**, igual que la
    retopologia: la cadena no deberia obligar a intentar algo para descubrir que
    no se puede.
    """
    if instalado():
        return None
    return f"falta el proveedor de textura ({PROVEEDOR}); {_NO_SE_SUSTITUYE}"


def exigir() -> None:
    """Falla antes de tocar un byte, diciendo que falta, para que y como se consigue."""
    if instalado():
        return
    raise ProveedorNoDisponible(
        f"falta el proveedor de textura ({PROVEEDOR}), que hace falta para proyectar los "
        "fotogramas reales sobre la malla — el color con su desgaste y su luz, que "
        "ningun generador da.\n"
        f"  se instala con: {INSTALACION}\n"
        f"  y {_NO_SE_SUSTITUYE}\n"
        "  `videomesh doctor` dice el resto del entorno de una vez"
    )
