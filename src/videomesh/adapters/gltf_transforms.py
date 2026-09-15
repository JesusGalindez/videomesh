"""El unico sitio donde VideoMesh habla la convencion de glTF — D32.

glTF serializa la matriz **por columnas**, con la traslacion en 12, 13 y 14. La
canonica va **por filas**, con la traslacion en 3, 7 y 11. No son
intercambiables, y la regla de D32 es semantica: no es «el cargador transpone y
el exportador transpone», porque una libreria puede normalizar la matriz antes de
exponerla y dos transposiciones sin dueno se cancelan o se duplican sin que nada
salte.

Del otro lado esta deuda no eran dos sitios: eran tres, y la geometria salia bien
colocada por casualidad. Aqui la ida y la vuelta van juntas a proposito, y una
prueba comprueba que ningun otro fichero de `src/videomesh` nombra glTF.
"""

from collections.abc import Sequence

from videomesh.domain.algebra import comprobar_matriz

__all__ = ["a_gltf", "de_gltf"]


def _transponer(matriz: Sequence[float]) -> list[float]:
    comprobar_matriz(matriz)
    return [matriz[columna * 4 + fila] for fila in range(4) for columna in range(4)]


def de_gltf(por_columnas: Sequence[float]) -> list[float]:
    """Lee una matriz de glTF y devuelve la canonica por filas."""
    return _transponer(por_columnas)


def a_gltf(por_filas: Sequence[float]) -> list[float]:
    """Escribe una matriz canonica en la convencion de glTF."""
    return _transponer(por_filas)
