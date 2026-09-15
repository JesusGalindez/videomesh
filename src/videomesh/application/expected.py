"""`expected.json`: lo que VideoMesh afirma de su propio cubo — V4, D23.

Es la columna que a D23 le faltaba desde agosto. De `cube-v1` no habia segunda
implementacion —lo escribio SoftSight y nadie mas lo habia vuelto a escribir—, asi
que la tercera comparacion no podia significar nada: dos lecturas que salen del
mismo codigo pueden coincidir y estar las dos mal.

**Es oraculo de prueba, no parte del paquete.** SoftSight no lo consume en
produccion, y por eso no vive dentro del paquete sellado ni aparece entre sus
artifacts.

Dos funciones separadas a proposito:

    medir_cube_v1(paquete)   lee el paquete de disco y dice que hay
    expected_generado()      escribe lo que se afirma

`medir` no lee el oraculo. Si lo leyera, la comparacion seria el codigo
comparandose consigo mismo, que es exactamente lo que D23 existe para evitar.
"""

import json
import pathlib
from collections.abc import Sequence
from typing import Any

from videomesh.application.cube_v1 import CAMARAS, generar_cube_v1
from videomesh.contracts.serialization import volcar_json
from videomesh.domain.algebra import aplicar
from videomesh.domain.camera import proyectar
from videomesh.domain.frames import resolver_marco
from videomesh.domain.malla import caja_envolvente
from videomesh.formatos.ply import leer_cabecera_ply
from videomesh.formatos.png import leer_dimensiones_png

__all__ = ["EXPECTED", "PUNTOS", "expected_generado", "medir_cube_v1"]

#: El oraculo commiteado. Fuera del paquete, porque no es del paquete.
EXPECTED = pathlib.Path(__file__).resolve().parents[3] / "fixtures" / "expected" / "cube-v1.json"

#: Los puntos de la fila 4 de D23, elegidos para que entre todos validen
#: intrinsecos, centro de pixel, orientacion y algebra a la vez.
PUNTOS: dict[str, tuple[float, float, float]] = {
    "centro": (0.0, 0.0, 0.0),
    "esquina superior": (0.5, 0.5, 0.5),
    "esquina inferior opuesta": (-0.5, -0.5, -0.5),
    "fuera de eje": (0.5, -0.5, 0.0),
    "cerca del borde": (0.5, 0.5, -0.5),
}

#: El sexto punto **depende de la camara**, y descubrirlo costo una prueba roja:
#: un punto fijo del mundo que este detras de una camara esta delante de las otras
#: tres. Se toma el doble de lejos en la direccion de cada una, que siempre queda a
#: su espalda. Sin este caso, un punto de atras proyectaria a un pixel plausible.
_DETRAS = "detras de la camara"

_DECIMALES = 6

#: Las convenciones de camara que se comparan. No los intrinsecos ni la pose: eso
#: es de cada productor. Esto es lo que tiene que coincidir para que dos paquetes
#: hablen de lo mismo.
_DE_LA_CAMARA = (
    "id",
    "imageArtifactId",
    "width",
    "height",
    "model",
    "cameraAxes",
    "pixelOrigin",
    "pixelCenter",
)


def _redondear(valores: Sequence[float]) -> list[float]:
    return [round(v, _DECIMALES) + 0.0 for v in valores]


def _leer_puntos_ply(ruta: pathlib.Path) -> list[tuple[float, float, float]]:
    """Los vertices de un PLY ASCII, leidos del fichero y no de quien lo escribio."""
    puntos: list[tuple[float, float, float]] = []
    cabecera = leer_cabecera_ply(ruta)
    with ruta.open(encoding="ascii") as fichero:
        for linea in fichero:
            if linea.strip() == "end_header":
                break
        for _ in range(cabecera["vertex"]):
            x, y, z = (float(c) for c in next(fichero).split())
            puntos.append((x, y, z))
    return puntos


def medir_cube_v1(paquete: pathlib.Path) -> dict[str, Any]:
    """Mide un paquete ya publicado: recuentos, cajas y camaras registradas.

    Lee el manifest y los ficheros. **No lee `expected.json`**: lo que se compara
    tiene que venir de sitios distintos o la comparacion no compara nada.
    """
    manifest = json.loads((paquete / "manifest.json").read_text(encoding="utf-8"))
    artifacts = {a["id"]: a for a in manifest["artifacts"]}

    vertices = _leer_puntos_ply(paquete / artifacts["mesh"]["path"])
    nube = _leer_puntos_ply(paquete / artifacts["sparse"]["path"])
    cabecera = leer_cabecera_ply(paquete / artifacts["mesh"]["path"])
    imagenes = [a for a in manifest["artifacts"] if a["type"] == "IMAGE"]

    for imagen in imagenes:
        ancho, alto = leer_dimensiones_png(paquete / imagen["path"])
        camara = next(c for c in manifest["cameras"] if c["imageArtifactId"] == imagen["id"])
        if (ancho, alto) != (camara["width"], camara["height"]):
            raise ValueError(
                f"la camara {camara['id']} declara {camara['width']}x{camara['height']} y el PNG "
                f"tiene {ancho}x{alto}: una foto con los intrinsecos girados se ve bien en "
                "miniatura (D33)"
            )

    minimo, maximo = caja_envolvente(vertices)
    minimo_nube, maximo_nube = caja_envolvente(nube)
    canonica = normalizar_caja(vertices, manifest["frameGraph"]["transforms"], "ASSET_CANONICAL")

    return {
        "recuentos": {
            "artifacts": len(manifest["artifacts"]),
            "malla": {
                "vertices": cabecera["vertex"],
                "triangulos": cabecera["face"],
                "verticesSoldados": len({tuple(v) for v in vertices}),
            },
            "nube": {"puntos": cabecera["vertex"] and len(nube)},
            "imagenes": len(imagenes),
        },
        "caja": {
            "malla": {"min": _redondear(minimo), "max": _redondear(maximo)},
            "nube": {"min": _redondear(minimo_nube), "max": _redondear(maximo_nube)},
            "enASSET_CANONICAL": canonica,
        },
        "camaras": [{campo: c[campo] for campo in _DE_LA_CAMARA} for c in manifest["cameras"]],
    }


def normalizar_caja(
    vertices: Sequence[tuple[float, float, float]],
    transformaciones: Sequence[dict[str, Any]],
    destino: str,
    origen: str = "RECONSTRUCTION",
) -> dict[str, list[float]] | None:
    """La caja en otro marco: **se transforman los vertices y se vuelve a medir**.

    Nunca se transforma la caja. Una caja rotada deja de estar alineada con los
    ejes, asi que rotar sus dos esquinas da otra cosa — sobre un cubo alineado a 30
    grados la diferencia es 0,683013 contra 0,5.

    Sin camino devuelve `None`, nunca la identidad (D11).
    """
    from videomesh.domain.frames import ErrorDeMarco

    try:
        matriz = resolver_marco(transformaciones, origen, destino)
    except ErrorDeMarco:
        return None
    movidos = [tuple(aplicar(matriz, v)) for v in vertices]
    minimo, maximo = caja_envolvente(movidos)  # type: ignore[arg-type]
    return {"min": _redondear(minimo), "max": _redondear(maximo)}


def _proyecciones() -> dict[str, dict[str, dict[str, Any]]]:
    afirmado: dict[str, dict[str, dict[str, Any]]] = {}
    for camara in CAMARAS:
        matriz = camara["worldFromCamera"]
        detras = (matriz[3] * 2.0, matriz[7] * 2.0, matriz[11] * 2.0)
        por_punto: dict[str, dict[str, Any]] = {}
        for nombre, punto in {**PUNTOS, _DETRAS: detras}.items():
            resultado = proyectar(camara, punto)
            por_punto[nombre] = {
                "punto": list(punto),
                "x": round(resultado.x, _DECIMALES) + 0.0,
                "y": round(resultado.y, _DECIMALES) + 0.0,
                "profundidad": round(resultado.profundidad, _DECIMALES) + 0.0,
                "dentro": resultado.dentro,
            }
        afirmado[str(camara["id"])] = por_punto
    return afirmado


def expected_generado(paquete: pathlib.Path | None = None) -> str:
    """El texto de `fixtures/expected/cube-v1.json` para el cubo de hoy."""
    import tempfile

    if paquete is None:
        with tempfile.TemporaryDirectory() as temporal:
            return expected_generado(generar_cube_v1(pathlib.Path(temporal) / "cube-v1"))

    documento = {
        "documentType": "videomesh.cube-v1-expected",
        "$comment": (
            "Oraculo de prueba de D23, no parte del paquete: SoftSight no lo consume en "
            "produccion. Lo escribe scripts/generar_expected.py y se compara contra lo que "
            "el consumidor mide del mismo paquete."
        ),
        "packageId": "cube-v1",
        **medir_cube_v1(paquete),
        "proyecciones": _proyecciones(),
    }
    return volcar_json(documento) + "\n"
