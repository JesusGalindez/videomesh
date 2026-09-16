"""La etapa `retopologia`, declarada **sin instrumento** — encargo 04, C1.

Los dos proveedores que el encargo nombra —Instant Meshes y QuadriFlow— no estan en
esta maquina y no se pueden poner: no estan en PyPI, y no hay brew ni cmake para
construirlos (comprobado el 2026-09-16). No es un problema de configuracion, es que
el instrumento no existe aqui.

Lo que **si** hay es el proveedor de malla que ya esta puesto, y no se usa. Conviene
que quede escrito antes de que a alguien le tiente:

```text
meshing_tri_to_quad_dominant   empareja triangulos en quads conservando los
                              vertices originales. No alinea con la forma, no
                              decima y no mueve un vertice: su distancia de
                              superficie seria cero y la etapa no tendria ninguna
                              perdida que publicar
```

Una etapa de quads que no dice cuanto costo es **peor** que una etapa declarada sin
instrumento, porque la primera parece hecha. Y el encargo lo dice con todas las
letras: no se sustituye el proveedor por otro que da menos.

Asi que esta etapa no se implementa: se declara. `exigir` es su frontera, con las
tres partes del mensaje que pide `providers/externos.py` —que falta, para que hace
falta y como se consigue—, y `motivo_de_ausencia` es lo que `status` publica para
que nadie tenga que lanzarla para enterarse de que no se puede.
"""

import shutil

from videomesh.domain.errores import ProveedorNoDisponible

__all__ = [
    "ETAPA",
    "INSTALACION",
    "ORDENES",
    "PROVEEDOR",
    "exigir",
    "instalado",
    "motivo_de_ausencia",
]

ETAPA = "retopologia"

PROVEEDOR = "instant-meshes|quadriflow"

#: Los nombres con los que puede estar en el PATH. Instant Meshes se construye como
#: `instant-meshes`; QuadriFlow, como `quadriflow`.
ORDENES = ("instant-meshes", "InstantMeshes", "instant_meshes", "quadriflow", "QuadriFlow")

INSTALACION = (
    "se construyen desde fuente: Instant Meshes (wjakob/instant-meshes, C++ y Eigen) o "
    "QuadriFlow (C++). Esta maquina no tiene brew ni cmake, asi que el primer paso es "
    "poner un sistema de construccion"
)

#: Por que no se sustituye, en una linea, para que viaje al informe y a `status`.
_NO_SE_SUSTITUYE = (
    "no se sustituye por el proveedor de malla: su unico corte de quads conserva los "
    "vertices originales, asi que no alinea con la forma y no tendria ninguna perdida que "
    "publicar"
)


def instalado() -> bool:
    """Si alguno de los dos proveedores esta en el PATH."""
    return any(shutil.which(orden) is not None for orden in ORDENES)


def motivo_de_ausencia() -> str | None:
    """Por que esta etapa no se puede hacer ahora, o `None` si si se puede.

    Lo lee `status` para publicarlo **sin lanzar la etapa**: el veredicto de la
    cadena no deberia depender de que alguien intente algo para descubrir que no.
    """
    if instalado():
        return None
    return f"falta el proveedor de retopologia ({PROVEEDOR}); {_NO_SE_SUSTITUYE}"


def exigir() -> None:
    """Falla antes de tocar un byte, diciendo que falta, para que y como se consigue."""
    if instalado():
        return
    raise ProveedorNoDisponible(
        f"falta el proveedor de retopologia ({PROVEEDOR}), que hace falta para convertir "
        "triangulos desordenados en quads alineados con la forma.\n"
        f"  se instala con: {INSTALACION}\n"
        f"  y {_NO_SE_SUSTITUYE}\n"
        "  `videomesh doctor` dice el resto del entorno de una vez"
    )
