"""Escritura de OBJ con color por vertice, que es lo que el horneado necesita.

Existe por una limitacion concreta y medida del proveedor de malla, no por gusto de
formato: para hornear un vector por vertice en el atlas hacen falta **el color y las
coordenadas de textura en el mismo fichero**. Se comprobo el 2026-09-16:

```text
PLY          lleva color por vertice y no lleva UV: un PLY no admite coordenadas
OBJ          lleva las dos cosas, pero el escritor del proveedor no pone el color
             por vertice — lo manda a una textura aparte, y entonces el color no
             viaja con la malla
GLB con COLOR_0   depende de que el lector del proveedor lo lea, y no se comprobo
```

El OBJ con `v x y z r g b` si lo lee: medido sobre el atlas de 10.649 vertices del
banco de pruebas, el proveedor carga el vertice con `has_vertex_color()` cierto y
las UV por esquina ciertas, y hornea el color sobre su propio atlas texel a texel
— un color constante sale constante en el 100 % de los texeles—. Es la forma que
el proveedor entiende, y por eso se escribe aqui en vez de inventar otra.

El color se escribe en coma flotante normalizada (0..1) porque es lo que el
formato espera ahi, y el redondeo a ocho bits lo hace el proveedor al hornear: el
que se publica es el que acaba en el mapa, no el que se pidio.
"""

import pathlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - solo para el analisis de tipos
    from numpy.typing import NDArray

__all__ = ["escribir_obj_coloreado"]


def escribir_obj_coloreado(
    destino: pathlib.Path,
    *,
    vertices: "NDArray[Any]",
    caras: "NDArray[Any]",
    uv: "NDArray[Any]",
    colores: "NDArray[Any]",
) -> None:
    """La malla con UV por esquina y un color por vertice, en el orden que el proveedor lee.

    Los indices del OBJ empiezan en 1 y van `vertice/textura`: cada esquina apunta a
    su UV, que es lo que deja al proveedor reconstruir el atlas tal y como se corto.
    """
    import numpy as np

    vertices = np.asarray(vertices, dtype="float64")
    caras = np.asarray(caras, dtype="int64")
    uv = np.asarray(uv, dtype="float64")
    colores = np.asarray(colores, dtype="float64")

    if caras.ndim != 2 or caras.shape[1] != 3:
        raise ValueError(f"el OBJ escribe triangulos y llegaron caras de {caras.shape}")
    if len(uv) != len(vertices) or len(colores) != len(vertices):
        raise ValueError(
            f"el OBJ necesita una UV y un color por vertice: {len(vertices)} vertices, "
            f"{len(uv)} UV y {len(colores)} colores"
        )

    lineas = ["# videomesh: color por vertice y UV por esquina"]
    lineas += [
        f"v {p[0]:.9g} {p[1]:.9g} {p[2]:.9g} {c[0]:.6g} {c[1]:.6g} {c[2]:.6g}"
        for p, c in zip(vertices, colores, strict=True)
    ]
    lineas += [f"vt {t[0]:.9g} {t[1]:.9g}" for t in uv]
    lineas += [
        f"f {a + 1}/{a + 1} {b + 1}/{b + 1} {c + 1}/{c + 1}"
        for a, b, c in caras.astype("int64")[:, :3].tolist()
    ]

    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="ascii") as salida:
        for linea in lineas:
            salida.write(linea + "\n")
