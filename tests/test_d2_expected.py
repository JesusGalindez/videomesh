"""D2 — V4: lo que VideoMesh afirma de su propio cubo.

Es la columna que a D23 le falta desde agosto. `expected.json` es **oraculo de
prueba, no parte del paquete**: SoftSight no lo consume en produccion, y por eso
no vive dentro del paquete sellado.

Lo que lo hace util no es que lo escriba este repositorio —eso solo probaria que
no ha cambiado— sino que la tercera comparacion de D23 lo enfrente a lo que
SoftSight mide del mismo paquete. De `cube-v1` no habia segunda implementacion: la
escribieron ellos y nadie mas lo habia vuelto a escribir. Esta es esa segunda.
"""

import json
import pathlib

import pytest

from videomesh.application.expected import (
    EXPECTED,
    expected_generado,
    medir_cube_v1,
)
from videomesh.contracts.generacion import ESQUEMAS

DORADOS = json.loads((ESQUEMAS / "fixtures" / "package-parity-v1.json").read_text())


def test_lo_commiteado_es_lo_que_el_generador_produce_hoy() -> None:
    """Si el cubo cambia y el oraculo no, rojo."""
    assert EXPECTED.read_text(encoding="utf-8") == expected_generado()


def test_es_determinista_entre_dos_generaciones() -> None:
    """V4 lo pide explicitamente: sin esto no afirma nada."""
    assert expected_generado() == expected_generado()


def test_no_vive_dentro_del_paquete(tmp_path: pathlib.Path) -> None:
    """No es parte del paquete: el consumidor no lo lee en produccion."""
    from videomesh.application.cube_v1 import generar_cube_v1

    paquete = generar_cube_v1(tmp_path / "cube-v1")
    assert not (paquete / "expected.json").exists()
    manifest = json.loads((paquete / "manifest.json").read_text(encoding="utf-8"))
    assert all("expected" not in a["path"] for a in manifest["artifacts"])


def test_afirma_los_recuentos_dorados() -> None:
    """Los mismos numeros que `package-parity-v1` publica para un cubo unidad."""
    afirmado = json.loads(expected_generado())["recuentos"]
    esperado = DORADOS["recuentos"]["cube-v1"]
    assert afirmado["artifacts"] == esperado["artifacts"]
    assert afirmado["imagenes"] == esperado["imagenes"]
    assert afirmado["malla"] == esperado["malla"]
    assert afirmado["nube"] == esperado["nube"]


def test_afirma_la_caja_dorada() -> None:
    afirmado = json.loads(expected_generado())["caja"]
    esperado = DORADOS["caja"]["cube-v1"]
    assert afirmado["malla"] == esperado["malla"]
    assert afirmado["nube"] == esperado["nube"]
    assert afirmado["enASSET_CANONICAL"] == esperado["enASSET_CANONICAL"]


def test_afirma_las_cuatro_camaras_con_sus_convenciones() -> None:
    """Las convenciones son las que un error no mueve: hay que declararlas y compararlas."""
    camaras = json.loads(expected_generado())["camaras"]
    assert len(camaras) == 4
    for camara in camaras:
        assert camara["width"] == camara["height"] == 256
        assert camara["model"] == "PINHOLE"
        assert camara["cameraAxes"] == "X_RIGHT_Y_UP_Z_BACKWARD"
        assert camara["pixelOrigin"] == "TOP_LEFT"
        assert camara["pixelCenter"] == "CENTER"


def test_afirma_la_proyeccion_de_puntos_conocidos() -> None:
    """La fila 4 de D23: centro, esquina, fuera de eje y cerca del borde."""
    proyecciones = json.loads(expected_generado())["proyecciones"]
    assert set(proyecciones) == {"frontal", "lateral", "superior", "oblicua"}
    for puntos in proyecciones.values():
        assert "centro" in puntos
        assert "detras de la camara" in puntos
        for valores in puntos.values():
            assert set(valores) == {"punto", "x", "y", "profundidad", "dentro"}


def test_el_punto_de_detras_esta_fuera_del_encuadre() -> None:
    """Si saliera dentro, la afirmacion seria falsa y nadie la miraria."""
    proyecciones = json.loads(expected_generado())["proyecciones"]
    for puntos in proyecciones.values():
        assert puntos["detras de la camara"]["dentro"] is False
        assert puntos["detras de la camara"]["profundidad"] < 0


def test_medir_no_lee_el_oraculo(tmp_path: pathlib.Path) -> None:
    """La medida sale del paquete en disco; si leyera el oraculo, se compararia consigo."""
    from videomesh.application.cube_v1 import generar_cube_v1

    paquete = generar_cube_v1(tmp_path / "cube-v1")
    medido = medir_cube_v1(paquete)
    assert medido["recuentos"]["malla"]["vertices"] == 24
    assert medido["caja"]["malla"]["min"] == [-0.5, -0.5, -0.5]


def test_el_oraculo_no_afirma_nada_que_no_se_pueda_comprobar() -> None:
    """Un oraculo con campos que nadie compara es un documento que envejece solo."""
    afirmado = json.loads(expected_generado())
    assert set(afirmado) == {
        "documentType",
        "$comment",
        "packageId",
        "recuentos",
        "caja",
        "camaras",
        "proyecciones",
    }


@pytest.mark.parametrize("campo", ["recuentos", "caja", "camaras"])
def test_lo_que_se_afirma_es_lo_que_se_mide(campo: str, tmp_path: pathlib.Path) -> None:
    """La primera de las tres comparaciones: VideoMesh contra su propio oraculo."""
    from videomesh.application.cube_v1 import generar_cube_v1

    paquete = generar_cube_v1(tmp_path / "cube-v1")
    assert medir_cube_v1(paquete)[campo] == json.loads(expected_generado())[campo]
