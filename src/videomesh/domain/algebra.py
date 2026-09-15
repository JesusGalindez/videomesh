"""Algebra canonica de transformaciones — D32.

    matriz          4x4 homogenea
    serializacion   por filas, 16 numeros, traslacion en 3, 7 y 11
    matematica      vectores columna
    composicion     p_destino = T_destino_desde_origen x p_origen

Aqui no se habla de ninguna otra convencion. La de glTF existe, es distinta y no
es intercambiable, y por eso vive sola en `adapters/gltf_transforms.py`: dos
sitios donde transponer son dos transposiciones que se cancelan, la geometria
sale bien colocada por casualidad y ningun hash lo delata.
"""

from collections.abc import Sequence

__all__ = ["IDENTIDAD", "aplicar", "componer", "comprobar_matriz", "es_rigida", "inversa_rigida"]

#: Traslacion nula, sin rotacion ni escala. Se registra igual (D11).
IDENTIDAD = [
    1.0, 0.0, 0.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 1.0, 0.0,
    0.0, 0.0, 0.0, 1.0,
]  # fmt: skip


def comprobar_matriz(matriz: Sequence[float]) -> None:
    """Una matriz que no son dieciseis numeros no es una matriz 4x4."""
    if len(matriz) != 16:
        raise ValueError(f"una matriz canonica son 16 numeros por filas, no {len(matriz)}")


def aplicar(matriz: Sequence[float], punto: Sequence[float]) -> list[float]:
    """Lleva un punto de tres coordenadas por la matriz: `p_destino = M x p_origen`.

    El punto entra como columna homogenea con `w = 1`, y la ultima fila tiene que
    ser (0, 0, 0, 1): en este contrato todas las transformaciones son afines.

    **No se divide por `w`.** Dividir convertiria una matriz mal leida en un punto
    plausible: la de glTF sin transponer trae la traslacion en la ultima fila, sale
    un `w` distinto de 1, y la division reescala el punto a algo que parece una
    medida. Rechazarlo hace ruidoso justo el fallo que D32 describe.
    """
    comprobar_matriz(matriz)
    if len(punto) != 3:
        raise ValueError(f"un punto son 3 coordenadas, no {len(punto)}")
    ultima = matriz[12:]
    if not all(abs(a - b) <= 1e-12 for a, b in zip(ultima, (0.0, 0.0, 0.0, 1.0), strict=True)):
        raise ValueError(
            f"la ultima fila es {list(ultima)} y tiene que ser (0, 0, 0, 1); "
            "una matriz de glTF sin transponer trae ahi su traslacion"
        )
    x, y, z = punto
    homogeneo = [
        matriz[fila * 4] * x
        + matriz[fila * 4 + 1] * y
        + matriz[fila * 4 + 2] * z
        + matriz[fila * 4 + 3]
        for fila in range(4)
    ]
    return homogeneo[:3]


def componer(
    destino_desde_medio: Sequence[float], medio_desde_origen: Sequence[float]
) -> list[float]:
    """`T_destino_desde_origen = T_destino_desde_medio x T_medio_desde_origen`.

    El orden es el del contrato y no es simetrico: al reves compone la otra
    transformacion, que tambien es una matriz valida y esta mal.
    """
    comprobar_matriz(destino_desde_medio)
    comprobar_matriz(medio_desde_origen)
    return [
        sum(
            destino_desde_medio[fila * 4 + k] * medio_desde_origen[k * 4 + columna]
            for k in range(4)
        )
        for fila in range(4)
        for columna in range(4)
    ]


def es_rigida(matriz: Sequence[float], tolerancia: float = 1e-9) -> bool:
    """Dice si la matriz es una rotacion mas una traslacion, sin escala ni proyeccion.

    Importa porque D11 pide que ida y vuelta den la identidad **exacta**, y eso solo
    lo cumple una transformacion cuya inversa se pueda escribir sin dividir: la de
    una rigida es la transpuesta de su rotacion. Una escala tiene inversa, pero
    inexacta, y una proyeccion no es una pose aunque los dieciseis numeros esten.
    """
    comprobar_matriz(matriz)
    if any(abs(a - b) > tolerancia for a, b in zip(matriz[12:], (0.0, 0.0, 0.0, 1.0), strict=True)):
        return False
    # R^T R tiene que ser la identidad: columnas ortonormales.
    for i in range(3):
        for j in range(3):
            producto = sum(matriz[k * 4 + i] * matriz[k * 4 + j] for k in range(3))
            if abs(producto - (1.0 if i == j else 0.0)) > tolerancia:
                return False
    return True


def inversa_rigida(matriz: Sequence[float]) -> list[float]:
    """La inversa de una transformacion rigida: `R^T` y `-R^T t`.

    Se escribe asi y no invirtiendo la matriz entera a proposito: no hay ninguna
    division, asi que la vuelta deshace la ida sin arrastrar el error que una
    eliminacion gaussiana dejaria.
    """
    comprobar_matriz(matriz)
    traslacion = (matriz[3], matriz[7], matriz[11])
    inversa = list(IDENTIDAD)
    for fila in range(3):
        for columna in range(3):
            inversa[fila * 4 + columna] = matriz[columna * 4 + fila]
        inversa[fila * 4 + 3] = -sum(matriz[eje * 4 + fila] * traslacion[eje] for eje in range(3))
    return inversa
