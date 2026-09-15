"""El CameraSet canonico: la camara dice de que imagen habla — D10, D19, D33.

`imageSpace`, `pixelOrigin`, `pixelCenter`, ejes, dimensiones, intrinsecos y
distorsion viajan como **una sola unidad** con `imageArtifactHash`. Suelto, cada
campo es plausible; junto es lo que impide combinar unos intrinsecos rectificados
con la imagen distorsionada, o una mascara del frame original con profundidad del
rectificado — errores que no se ven, porque las dos imagenes tienen el mismo
tamano y el mismo aspecto.

`transformConvention` **no** se declara por camara: D32 ya la fija para todo el
repositorio. Repetirla aqui seria un segundo original de la misma decision.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from videomesh.domain.algebra import comprobar_matriz
from videomesh.domain.errores import ErrorDeContrato

__all__ = ["ErrorDeCamara", "Proyeccion", "comprobar_camaras", "proyectar"]


class ErrorDeCamara(ErrorDeContrato, ValueError):
    """La camara describe pixeles que no son los suyos, o no se sabe cuales."""


@dataclass(frozen=True)
class Proyeccion:
    """Donde cae un punto del mundo en la rejilla de una camara."""

    x: float
    y: float
    profundidad: float
    dentro: bool


def proyectar(camara: Mapping[str, Any], punto: Sequence[float]) -> Proyeccion:
    """Proyecta un punto del mundo a pixeles: `p_cam = R^T (p - t)`.

    R y t se leen de `worldFromCamera`, 4x4 por filas con la traslacion en 3, 7 y
    11 (D32). La transpuesta es la inversa porque R es una rotacion, y se usa asi
    a proposito: invertir la matriz entera admitiria una escala que en una pose no
    deberia existir.
    """
    matriz = camara["worldFromCamera"]
    comprobar_matriz(matriz)
    if len(punto) != 3:
        raise ErrorDeCamara(f"un punto son 3 coordenadas, no {len(punto)}")

    traslacion = (matriz[3], matriz[7], matriz[11])
    relativo = [p - t for p, t in zip(punto, traslacion, strict=True)]
    # R^T p: la columna j de R es la fila j leida hacia abajo, asi que el producto
    # con la transpuesta recorre la columna.
    en_camara = [
        sum(matriz[fila * 4 + eje] * relativo[fila] for fila in range(3)) for eje in range(3)
    ]

    ejes = camara["cameraAxes"]
    if ejes == "X_RIGHT_Y_UP_Z_BACKWARD":
        profundidad = -en_camara[2]
        altura = -en_camara[1]
    elif ejes == "X_RIGHT_Y_DOWN_Z_FORWARD":
        profundidad = en_camara[2]
        altura = en_camara[1]
    else:
        raise ErrorDeCamara(f"cameraAxes desconocido: {ejes!r}")

    if profundidad == 0:
        raise ErrorDeCamara("el punto esta en el plano de la camara: profundidad 0")

    intrinsecos = camara["intrinsics"]
    x = intrinsecos["fx"] * (en_camara[0] / profundidad) + intrinsecos["cx"]
    y = intrinsecos["fy"] * (altura / profundidad) + intrinsecos["cy"]

    if camara["pixelCenter"] == "CORNER":
        x -= 0.5
        y -= 0.5
    if camara["pixelOrigin"] == "BOTTOM_LEFT":
        y = camara["height"] - y

    dentro = profundidad > 0 and 0 <= x <= camara["width"] and 0 <= y <= camara["height"]
    return Proyeccion(x=x, y=y, profundidad=profundidad, dentro=dentro)


def comprobar_camaras(paquete: Mapping[str, Any]) -> None:
    """Comprueba que cada camara habla de una imagen que esta en el paquete.

    Es la mitad de D10 que solo se puede ejercer con el paquete entero delante:
    el esquema ve que el hash es un texto de 64 caracteres, no que sea el hash de
    *esa* imagen.
    """
    artifacts = {a["id"]: a for a in paquete.get("artifacts", [])}
    vistas: set[str] = set()

    for camara in paquete.get("cameras", []):
        identidad = camara["id"]
        if identidad in vistas:
            raise ErrorDeCamara(f"la camara {identidad} esta declarada dos veces")
        vistas.add(identidad)

        nombrado = camara["imageArtifactId"]
        imagen = artifacts.get(nombrado)
        if imagen is None:
            raise ErrorDeCamara(
                f"la camara {identidad} nombra {nombrado}, que no esta en el paquete"
            )
        if imagen["type"] != "IMAGE":
            raise ErrorDeCamara(
                f"la camara {identidad} nombra {nombrado}, que es {imagen['type']} y no IMAGE: "
                "unos intrinsecos sobre algo que no son pixeles no significan nada"
            )
        if camara["imageArtifactHash"] != imagen["sha256"]:
            raise ErrorDeCamara(
                f"el imageArtifactHash de {identidad} no es el de {nombrado}: "
                "los intrinsecos describirian una imagen que no es la suya"
            )
        if camara["imageSpace"] == "RECTIFIED" and camara.get("distortion"):
            raise ErrorDeCamara(
                f"la camara {identidad} declara RECTIFIED y trae distorsion: "
                "si la imagen ya esta rectificada no queda nada que corregir"
            )
