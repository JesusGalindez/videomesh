"""B2 — D10, D19 y D33: la camara dice de que imagen habla, y se comprueba.

`imageArtifactHash` ata la camara a **los pixeles y no a un nombre**. Un id se
reapunta a otro fichero sin que nada chille, y entonces los intrinsecos describen
una imagen que no es la suya. La puerta lo ejerce cambiando el hash de una camara
por el de otra imagen del mismo paquete —mismo tamano, misma camara, todo
plausible— y tiene que salir rechazado.

La proyeccion se comprueba contra `camera-projection-v1`, que son cuatro camaras
por seis puntos de valores dorados calculados del otro lado. Hasta ese fixture las
convenciones de `cube-v1` eran una afirmacion sin puerta: escribirlo encontro un
error de verdad —imagenes ortograficas con un manifest que declaraba PINHOLE—, y
con un cubo alineado no se nota. Lo delato la vista de tres cuartos.
"""

import json
from typing import Any

import pytest

from videomesh.contracts.generacion import ESQUEMAS
from videomesh.domain.camera import (
    ErrorDeCamara,
    comprobar_camaras,
    proyectar,
)

FIXTURE = json.loads(
    (ESQUEMAS / "fixtures" / "camera-projection-v1.json").read_text(encoding="utf-8")
)
CAMARAS = {c["id"]: c for c in FIXTURE["cameras"]}
MANIFEST = json.loads(
    (ESQUEMAS.parent / "artifacts" / "cube-v1" / "manifest.json").read_text(encoding="utf-8")
)

#: Los valores dorados vienen redondeados a seis decimales. La tolerancia es esa,
#: declarada y no supuesta: comparar mas fino seria comparar contra el redondeo.
TOLERANCIA = 1e-6

CASOS = [
    pytest.param(camara, nombre, valores, id=f"{camara} · {nombre}")
    for camara, puntos in FIXTURE["expected"].items()
    for nombre, valores in puntos.items()
]


@pytest.mark.parametrize(("camara", "nombre", "esperado"), CASOS)
def test_los_veinticuatro_valores_dorados(
    camara: str, nombre: str, esperado: dict[str, Any]
) -> None:
    obtenido = proyectar(CAMARAS[camara], esperado["point"])
    assert obtenido.x == pytest.approx(esperado["x"], abs=TOLERANCIA)
    assert obtenido.y == pytest.approx(esperado["y"], abs=TOLERANCIA)
    assert obtenido.profundidad == pytest.approx(esperado["depth"], abs=TOLERANCIA)


def test_un_punto_detras_de_la_camara_no_esta_dentro() -> None:
    """Profundidad negativa. Sin esto, un punto a la espalda proyecta a un pixel plausible."""
    detras = FIXTURE["expected"]["cam-frontal"]["detrás de la cámara"]
    resultado = proyectar(CAMARAS["cam-frontal"], detras["point"])
    assert resultado.profundidad < 0
    assert not resultado.dentro


def test_un_punto_del_encuadre_si_esta_dentro() -> None:
    centro = FIXTURE["expected"]["cam-frontal"]["centro"]
    assert proyectar(CAMARAS["cam-frontal"], centro["point"]).dentro


def test_pixel_center_corner_resta_medio_pixel_a_las_dos_coordenadas() -> None:
    """Lo dice la formula del fixture. Ninguna de sus camaras lo ejerce; aqui si."""
    dorado = FIXTURE["expected"]["cam-tres-cuartos"]["esquina superior"]
    esquina = dict(CAMARAS["cam-tres-cuartos"], pixelCenter="CORNER")
    obtenido = proyectar(esquina, dorado["point"])
    assert obtenido.x == pytest.approx(dorado["x"] - 0.5, abs=TOLERANCIA)
    assert obtenido.y == pytest.approx(dorado["y"] - 0.5, abs=TOLERANCIA)


def test_pixel_origin_bottom_left_cuenta_la_fila_desde_el_otro_extremo() -> None:
    dorado = FIXTURE["expected"]["cam-tres-cuartos"]["esquina superior"]
    camara = CAMARAS["cam-tres-cuartos"]
    obtenido = proyectar(dict(camara, pixelOrigin="BOTTOM_LEFT"), dorado["point"])
    assert obtenido.x == pytest.approx(dorado["x"], abs=TOLERANCIA)
    assert obtenido.y == pytest.approx(camara["height"] - dorado["y"], abs=TOLERANCIA)


def _en_ejes_de_computer_vision(camara: dict[str, Any]) -> dict[str, Any]:
    """La MISMA camara fisica escrita en el otro convenio: Y y Z de R cambian de signo."""
    matriz = list(camara["worldFromCamera"])
    for fila in range(3):
        matriz[fila * 4 + 1] = -matriz[fila * 4 + 1]
        matriz[fila * 4 + 2] = -matriz[fila * 4 + 2]
    return dict(camara, worldFromCamera=matriz)


def test_la_misma_camara_en_el_otro_convenio_proyecta_igual() -> None:
    """Si no diera lo mismo, el convenio no seria un convenio sino otra camara."""
    dorado = FIXTURE["expected"]["cam-tres-cuartos"]["esquina superior"]
    otra = _en_ejes_de_computer_vision(CAMARAS["cam-tres-cuartos"])
    obtenido = proyectar(dict(otra, cameraAxes="X_RIGHT_Y_DOWN_Z_FORWARD"), dorado["point"])
    assert obtenido.x == pytest.approx(dorado["x"], abs=TOLERANCIA)
    assert obtenido.y == pytest.approx(dorado["y"], abs=TOLERANCIA)
    assert obtenido.profundidad == pytest.approx(dorado["depth"], abs=TOLERANCIA)


@pytest.mark.parametrize("camara", sorted(CAMARAS))
def test_confundir_los_ejes_manda_el_objeto_detras_de_la_camara(camara: str) -> None:
    """Esa misma matriz con la etiqueta equivocada. El fallo que D10 nombra.

    No sale una imagen torcida: la profundidad cambia de signo en las cuatro
    camaras, asi que el objeto pasa a estar a la espalda. Y el pixel sigue siendo
    plausible —a veces el mismo—, que es lo que hace que nadie lo vea.
    """
    dorado = FIXTURE["expected"][camara]["esquina superior"]
    obtenido = proyectar(_en_ejes_de_computer_vision(CAMARAS[camara]), dorado["point"])
    assert obtenido.profundidad == pytest.approx(-dorado["depth"], abs=TOLERANCIA)
    assert not obtenido.dentro


def test_confundir_los_ejes_refleja_el_pixel_sobre_el_punto_principal() -> None:
    """Y sobre un objeto simetrico las dos imagenes parecen igual de correctas.

    En `cam-tres-cuartos` el reflejo ni se mueve —el punto cae en el eje— y solo
    se delata por la profundidad. Por eso `cameraAxes` no tiene valor por defecto.
    """
    camara = CAMARAS["cam-frontal"]
    dorado = FIXTURE["expected"]["cam-frontal"]["esquina superior"]
    obtenido = proyectar(_en_ejes_de_computer_vision(camara), dorado["point"])
    assert obtenido.x == pytest.approx(2 * camara["intrinsics"]["cx"] - dorado["x"], abs=TOLERANCIA)
    assert obtenido.y == pytest.approx(dorado["y"], abs=TOLERANCIA)


def test_el_manifest_de_cube_v1_tiene_las_camaras_atadas_a_sus_imagenes() -> None:
    comprobar_camaras(MANIFEST)


def test_reapuntar_el_hash_a_otra_imagen_del_mismo_paquete_se_rechaza() -> None:
    """El caso propio de B2, y el que D10 llama plausible: mismo tamano, misma camara."""
    paquete = json.loads(json.dumps(MANIFEST))
    otra = next(a for a in paquete["artifacts"] if a["id"] == "img-cam-lateral")
    frontal = next(c for c in paquete["cameras"] if c["id"] == "cam-frontal")
    frontal["imageArtifactHash"] = otra["sha256"]
    with pytest.raises(ErrorDeCamara, match="imageArtifactHash"):
        comprobar_camaras(paquete)


def test_una_camara_que_nombra_un_artifact_que_no_existe_se_rechaza() -> None:
    paquete = json.loads(json.dumps(MANIFEST))
    paquete["cameras"][0]["imageArtifactId"] = "img-que-no-existe"
    with pytest.raises(ErrorDeCamara, match="img-que-no-existe"):
        comprobar_camaras(paquete)


def test_una_camara_que_nombra_algo_que_no_es_una_imagen_se_rechaza() -> None:
    """Los intrinsecos de una malla no significan nada."""
    paquete = json.loads(json.dumps(MANIFEST))
    malla = next(a for a in paquete["artifacts"] if a["id"] == "mesh")
    paquete["cameras"][0]["imageArtifactId"] = malla["id"]
    paquete["cameras"][0]["imageArtifactHash"] = malla["sha256"]
    with pytest.raises(ErrorDeCamara, match="IMAGE"):
        comprobar_camaras(paquete)


def test_intrinsecos_rectificados_con_distorsion_se_contradicen() -> None:
    """Si la imagen ya esta rectificada no queda nada que corregir (D10)."""
    paquete = json.loads(json.dumps(MANIFEST))
    paquete["cameras"][0]["imageSpace"] = "RECTIFIED"
    paquete["cameras"][0]["distortion"] = {"k1": 0.12, "k2": -0.08}
    with pytest.raises(ErrorDeCamara, match="RECTIFIED"):
        comprobar_camaras(paquete)


def test_rectificada_sin_distorsion_pasa() -> None:
    """Lo que separa una regla de un rechazo indiscriminado."""
    paquete = json.loads(json.dumps(MANIFEST))
    paquete["cameras"][0]["imageSpace"] = "RECTIFIED"
    comprobar_camaras(paquete)


def test_dos_camaras_con_el_mismo_identificador_se_rechazan() -> None:
    paquete = json.loads(json.dumps(MANIFEST))
    paquete["cameras"].append(dict(paquete["cameras"][0]))
    with pytest.raises(ErrorDeCamara, match="cam-frontal"):
        comprobar_camaras(paquete)


def test_nada_aguas_abajo_interpreta_pixeles_a_partir_de_sourceOrientation() -> None:
    """D33, la mitad que comprueba una ausencia.

    `sourceOrientation` es provenance: la orientacion ya esta horneada en los
    pixeles y `width`/`height` describen la rejilla real. Un uso de este campo
    **no rompe ninguna prueba** —da una imagen girada que sigue siendo una imagen,
    y ningun hash lo delata—, asi que la unica forma de vigilarlo es esta, igual
    que D32 vigila su formula de transposicion.
    """
    import pathlib

    codigo = pathlib.Path(__file__).resolve().parents[1] / "src" / "videomesh"
    lo_nombran = {
        ruta.relative_to(codigo).as_posix()
        for ruta in codigo.rglob("*.py")
        if "sourceOrientation" in ruta.read_text(encoding="utf-8")
    }
    assert lo_nombran == {"contracts/modelos/reconstruction_package.py"}
