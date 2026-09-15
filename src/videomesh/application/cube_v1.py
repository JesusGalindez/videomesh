"""`cube-v1`: el cubo que VideoMesh fabrica, sus cuatro camaras y sus renders — V3.

Se **fabrica**, no se reconstruye. Reconstruir es del Sprint 2, y mezclarlo aqui
haria que el fixture de la frontera dependiera de la fotogrametria, que es
justamente lo que R0 existe para no necesitar.

Las cuatro vistas no son decorativas. D18 obliga a que ninguna imagen sea un
lienzo del color de fondo —pasaria los hashes igual de bien y seria evidencia
falsa— y la oblicua es la que delata una convencion equivocada: con el cubo
alineado a los ejes, una pose mal escrita se ve bien.

Los intrinsecos salen de una sola eleccion: campo de vision de 40 grados sobre una
rejilla de 256, que da `fx = 128 / tan(20 grados)`. La distancia es 3, lo bastante
para que la esfera que envuelve el cubo —radio raiz(3)/2— quepa entera desde
cualquier angulo con margen.
"""

import math
import pathlib
from collections.abc import Sequence
from typing import Any

from videomesh.domain.algebra import IDENTIDAD
from videomesh.domain.camera import proyectar
from videomesh.domain.malla import Malla, Punto, cubo_unidad, esquinas_del_cubo
from videomesh.formatos.ply import escribir_ply_malla, escribir_ply_nube
from videomesh.formatos.png import Color, escribir_png
from videomesh.project.sellado import publicar_paquete

__all__ = [
    "CAMARAS",
    "CAMPO_DE_VISION",
    "DISTANCIA",
    "FONDO",
    "LADO",
    "colores_de_cara",
    "generar_cube_v1",
    "render_de",
]

#: Lado de la rejilla, en pixeles.
LADO = 256

#: Campo de vision horizontal, en grados.
CAMPO_DE_VISION = 40.0

#: A que distancia del centro se ponen las camaras.
DISTANCIA = 3.0

#: Un gris que ningun color de cara usa: asi «es fondo» no es ambiguo.
FONDO: Color = (24, 24, 28)

_FOCAL = (LADO / 2) / math.tan(math.radians(CAMPO_DE_VISION / 2))


def colores_de_cara() -> list[Color]:
    """Un color por cara, en el orden en que `cubo_unidad` las emite.

    Distintos entre si a proposito: dos caras del mismo color harian que una vista
    de tres caras pareciera de dos, y esa es la comprobacion que separa una pose
    correcta de una plausible.
    """
    return [
        (214, 90, 78),
        (232, 168, 72),
        (120, 186, 108),
        (96, 152, 214),
        (168, 118, 196),
        (226, 226, 220),
    ]


def _mirando_al_origen(posicion: Punto) -> list[float]:
    """`worldFromCamera` de una camara colocada ahi y apuntando al centro.

    Los ejes son los de graficos —X a la derecha, Y arriba, Z hacia atras—, asi que
    la tercera columna de la rotacion es el vector que va del origen a la camara.
    """
    hacia_atras = _normalizar(posicion)
    arriba_provisional = (0.0, 1.0, 0.0)
    if abs(_producto(hacia_atras, arriba_provisional)) > 0.999:
        # Mirando desde el polo: cualquier «arriba» vertical es ambiguo.
        arriba_provisional = (0.0, 0.0, -1.0)
    derecha = _normalizar(_cruz(arriba_provisional, hacia_atras))
    arriba = _cruz(hacia_atras, derecha)

    matriz = list(IDENTIDAD)
    for fila in range(3):
        matriz[fila * 4] = derecha[fila]
        matriz[fila * 4 + 1] = arriba[fila]
        matriz[fila * 4 + 2] = hacia_atras[fila]
        matriz[fila * 4 + 3] = posicion[fila]
    return matriz


def _normalizar(vector: Sequence[float]) -> Punto:
    norma = math.sqrt(sum(c * c for c in vector))
    return (vector[0] / norma, vector[1] / norma, vector[2] / norma)


def _cruz(a: Sequence[float], b: Sequence[float]) -> Punto:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _producto(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def _camara(identidad: str, posicion: Punto) -> dict[str, Any]:
    return {
        "id": identidad,
        "imageArtifactId": f"img-{identidad}",
        "imageSpace": "ORIGINAL",
        "width": LADO,
        "height": LADO,
        "pixelOrigin": "TOP_LEFT",
        "pixelCenter": "CENTER",
        "model": "PINHOLE",
        "cameraAxes": "X_RIGHT_Y_UP_Z_BACKWARD",
        "intrinsics": {"fx": _FOCAL, "fy": _FOCAL, "cx": LADO / 2, "cy": LADO / 2},
        "worldFromCamera": _mirando_al_origen(posicion),
    }


_OBLICUA = DISTANCIA / math.sqrt(3.0)

#: Cuatro puntos de vista. La oblicua ve tres caras, que es la que sirve de puerta.
CAMARAS: list[dict[str, Any]] = [
    _camara("frontal", (0.0, 0.0, DISTANCIA)),
    _camara("lateral", (DISTANCIA, 0.0, 0.0)),
    _camara("superior", (0.0, DISTANCIA, 0.0)),
    _camara("oblicua", (_OBLICUA, _OBLICUA, _OBLICUA)),
]

_POR_ID = {camara["id"]: camara for camara in CAMARAS}


def render_de(identidad: str, malla: Malla | None = None) -> list[Color]:
    """Rasteriza el cubo desde una camara. Un color por cara y z-buffer por pixel.

    No es un motor de render y no pretende serlo: lo que la evidencia necesita es
    que la imagen muestre el objeto desde donde la camara dice, no sombreado.
    """
    camara = _POR_ID[identidad]
    geometria = malla if malla is not None else cubo_unidad()
    colores = colores_de_cara()

    pixeles: list[Color] = [FONDO] * (LADO * LADO)
    profundidades = [math.inf] * (LADO * LADO)

    for indice, (a, b, c) in enumerate(geometria.triangulos):
        color = colores[(indice // 2) % len(colores)]
        esquinas = [proyectar(camara, geometria.vertices[v]) for v in (a, b, c)]
        if any(e.profundidad <= 0 for e in esquinas):
            continue
        _pintar(pixeles, profundidades, esquinas, color)

    return pixeles


def _pintar(
    pixeles: list[Color],
    profundidades: list[float],
    esquinas: Sequence[Any],
    color: Color,
) -> None:
    """Rellena un triangulo por coordenadas baricentricas, con prueba de profundidad."""
    xs = [e.x for e in esquinas]
    ys = [e.y for e in esquinas]
    area = (xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0])
    if area == 0:
        return

    desde_x = max(0, math.floor(min(xs)))
    hasta_x = min(LADO - 1, math.ceil(max(xs)))
    desde_y = max(0, math.floor(min(ys)))
    hasta_y = min(LADO - 1, math.ceil(max(ys)))

    for fila in range(desde_y, hasta_y + 1):
        for columna in range(desde_x, hasta_x + 1):
            px, py = columna + 0.5, fila + 0.5
            w0 = ((xs[1] - px) * (ys[2] - py) - (xs[2] - px) * (ys[1] - py)) / area
            w1 = ((xs[2] - px) * (ys[0] - py) - (xs[0] - px) * (ys[2] - py)) / area
            w2 = 1.0 - w0 - w1
            if w0 < 0 or w1 < 0 or w2 < 0:
                continue
            profundidad = (
                w0 * esquinas[0].profundidad
                + w1 * esquinas[1].profundidad
                + w2 * esquinas[2].profundidad
            )
            posicion = fila * LADO + columna
            if profundidad < profundidades[posicion]:
                profundidades[posicion] = profundidad
                pixeles[posicion] = color


def generar_cube_v1(destino: pathlib.Path, *, package_id: str = "cube-v1") -> pathlib.Path:
    """Fabrica el paquete entero y lo publica sellado. Devuelve la ruta final.

    El orden lo impone D29 y lo hace cumplir `publicar_paquete`: primero los
    ficheros, luego sus hashes, y el manifest el ultimo.
    """
    malla = cubo_unidad()

    with publicar_paquete(destino, package_id=package_id, producer="videomesh/cube-v1") as obra:
        (obra.raiz / "images").mkdir()

        escribir_ply_malla(obra.raiz / "mesh.ply", malla)
        obra.anadir("mesh.ply", identidad="mesh", tipo="TRIANGLE_MESH", purely_reconstructed=True)

        escribir_ply_nube(obra.raiz / "sparse.ply", esquinas_del_cubo())
        obra.anadir("sparse.ply", identidad="sparse", tipo="POINT_CLOUD")

        for camara in CAMARAS:
            ruta = f"images/{camara['id']}.png"
            escribir_png(
                obra.raiz / ruta, ancho=LADO, alto=LADO, pixeles=render_de(camara["id"], malla)
            )
            imagen = obra.anadir(ruta, identidad=camara["imageArtifactId"], tipo="IMAGE")
            # El hash ata la camara a **los pixeles** y no a un nombre (D10), asi
            # que solo se puede rellenar cuando el fichero ya esta escrito.
            obra.cameras.append(dict(camara, imageArtifactHash=imagen["sha256"]))

        obra.manifest["scale"] = {"status": "RELATIVE", "source": "NONE"}
        obra.manifest["frameGraph"] = {
            "transforms": [
                {
                    "from": "RECONSTRUCTION",
                    "to": "ASSET_CANONICAL",
                    "matrix": list(IDENTIDAD),
                    "reason": "el cubo se fabrica ya en el marco canonico; la identidad se "
                    "registra igual, porque una transformacion sin registrar no existe (D11)",
                    "producer": "videomesh/cube-v1",
                }
            ]
        }
        obra.manifest["requiredEvidence"] = ["mesh"]

    return destino
