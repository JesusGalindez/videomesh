"""La geometria del cubo que VideoMesh fabrica — D1 del encargo, V3.

`cube-v1` se **fabrica**, no se reconstruye: reconstruir es del Sprint 2. Lo que
tiene que salir son los recuentos dorados de `package-parity-v1`: 24 vertices, 12
triangulos, 8 posiciones distintas y una caja de +-0,5.

24 y 8 no se contradicen. Cada esquina aparece **tres veces, una por cara**,
porque las normales por cara no se pueden compartir: un vertice unico tendria que
llevar tres normales a la vez. Un lector que suelde al leer contaria 8 y no
estaria mal — son dos preguntas distintas, y por eso se responden las dos.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = ["Malla", "Punto", "caja_envolvente", "cubo_unidad", "esquinas_del_cubo", "soldar"]

Punto = tuple[float, float, float]

#: Semilado del cubo unidad, centrado en el origen.
_SEMILADO = 0.5


@dataclass(frozen=True)
class Malla:
    """Vertices y triangulos, con los indices apuntando a la lista de vertices."""

    vertices: list[Punto]
    triangulos: list[tuple[int, int, int]]


def esquinas_del_cubo() -> list[Punto]:
    """Las ocho esquinas, en orden fijo. Es tambien la nube dispersa del paquete."""
    lado = (-_SEMILADO, _SEMILADO)
    return [(x, y, z) for x in lado for y in lado for z in lado]


def cubo_unidad() -> Malla:
    """El cubo con los vertices partidos por cara: 24 entradas y 12 triangulos.

    Las seis caras se enumeran por su eje y su signo, y cada una se escribe con
    sus cuatro esquinas en sentido antihorario vista desde fuera, para que la
    normal se aparte del centro. Una cara al reves da un cubo que por dentro
    parece cerrado y por fuera no.
    """
    vertices: list[Punto] = []
    triangulos: list[tuple[int, int, int]] = []

    for eje in range(3):
        for signo in (1.0, -1.0):
            # Los otros dos ejes, en el orden que deja la normal hacia fuera.
            u, v = ((eje + 1) % 3, (eje + 2) % 3) if signo > 0 else ((eje + 2) % 3, (eje + 1) % 3)
            base = len(vertices)
            for du, dv in ((-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)):
                punto = [0.0, 0.0, 0.0]
                punto[eje] = signo * _SEMILADO
                punto[u] = du * _SEMILADO
                punto[v] = dv * _SEMILADO
                vertices.append((punto[0], punto[1], punto[2]))
            triangulos.append((base, base + 1, base + 2))
            triangulos.append((base, base + 2, base + 3))

    return Malla(vertices=vertices, triangulos=triangulos)


def soldar(vertices: Sequence[Punto]) -> list[Punto]:
    """Las posiciones distintas, en el orden en que aparecen.

    Sin redondeo: los vertices del cubo son exactamente los mismos numeros, y una
    tolerancia aqui seria una decision de reparacion disfrazada de lectura.
    """
    vistos: dict[Punto, None] = {}
    for vertice in vertices:
        vistos.setdefault(tuple(vertice), None)  # type: ignore[arg-type]
    return list(vistos)


def caja_envolvente(vertices: Sequence[Punto]) -> tuple[list[float], list[float]]:
    """Minimo y maximo por eje. Sobre los vertices, nunca sobre otra caja.

    Importa para D23: una caja rotada deja de estar alineada con los ejes, asi que
    transformar sus dos esquinas da otra cosa. Se transforman los vertices y se
    vuelve a medir.
    """
    if not vertices:
        raise ValueError("una caja envolvente de cero vertices no existe")
    for vertice in vertices:
        for coordenada in vertice:
            if not math.isfinite(coordenada):
                raise ValueError(f"un vertice tiene {coordenada}, que no es un numero finito")
    return (
        [min(v[eje] for v in vertices) for eje in range(3)],
        [max(v[eje] for v in vertices) for eje in range(3)],
    )
