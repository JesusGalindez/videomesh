"""D1 — V3: el `cube-v1` de VideoMesh, consumido por SoftSight de verdad.

La puerta de esta tarea no es una afirmacion de este repositorio: es que el
consumidor real lo acepte.

    node ../Dron/softsight/tools/reconstruction.mjs inspect <ruta>/manifest.json

con `COMPLETE + PASS` y salida 0. Un paquete que SoftSight rechaza esta mal aunque
el codigo de aqui crea que no.
"""

import json
import pathlib
import shutil
import subprocess
from typing import Any

import pytest

from videomesh.application.cube_v1 import generar_cube_v1
from videomesh.contracts.generacion import ESQUEMAS

Informe = dict[str, Any]

CONSUMIDOR = ESQUEMAS.parent / "tools" / "reconstruction.mjs"
DORADOS = json.loads((ESQUEMAS / "fixtures" / "package-parity-v1.json").read_text())

necesita_node = pytest.mark.skipif(
    shutil.which("node") is None or not CONSUMIDOR.exists(),
    reason="hace falta node y el consumidor de SoftSight",
)


@pytest.fixture(scope="module")
def paquete(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    return generar_cube_v1(tmp_path_factory.mktemp("publicado") / "cube-v1")


@pytest.fixture(scope="module")
def informe(paquete: pathlib.Path) -> Informe:
    """El informe que devuelve el consumidor real, no una simulacion de el."""
    if shutil.which("node") is None or not CONSUMIDOR.exists():
        pytest.skip("hace falta node y el consumidor de SoftSight")
    salida = subprocess.run(
        ["node", str(CONSUMIDOR), "inspect", str(paquete / "manifest.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert salida.returncode == 0, salida.stderr[-2000:]
    informe: Informe = json.loads(salida.stdout)
    return informe


@necesita_node
def test_softsight_lo_acepta_completo_y_certificado(informe: Informe) -> None:
    """Lo que cierra D1 y el hito 2 del contrato."""
    assert informe["execution"] == "COMPLETE"
    assert informe["certification"] == "PASS"


@necesita_node
def test_el_informe_mide_los_recuentos_dorados(informe: Informe) -> None:
    esperado = DORADOS["recuentos"]["cube-v1"]["malla"]
    medida = informe["measurements"][0]
    assert medida["vertices"] == esperado["vertices"]
    assert medida["triangles"] == esperado["triangulos"]
    assert medida["vertices"] - medida["duplicatePositions"] == esperado["verticesSoldados"]


@necesita_node
def test_la_malla_sale_cerrada_y_sin_triangulos_degenerados(informe: Informe) -> None:
    """Es lo que hace que el cubo sirva de fixture: no tiene nada raro que explicar."""
    medida = informe["measurements"][0]
    assert medida["watertight"] is True
    assert medida["boundaryEdges"] == 0
    assert medida["nonManifoldEdges"] == 0
    assert medida["degenerateTriangles"] == 0


@necesita_node
def test_la_caja_medida_es_la_dorada(informe: Informe) -> None:
    esperada = DORADOS["caja"]["cube-v1"]["malla"]
    medida = informe["measurements"][0]
    assert medida["boundingBoxMin"] == esperada["min"]
    assert medida["boundingBoxMax"] == esperada["max"]


@necesita_node
def test_las_cuatro_camaras_llegan_con_su_imagen(informe: Informe) -> None:
    """`withImage` menor que `declared` seria una camara hablando de nada."""
    assert informe["cameras"] == {"declared": 4, "withImage": 4}


@necesita_node
def test_el_grafo_se_lee_y_los_dos_marcos_son_alcanzables(informe: Informe) -> None:
    marcos = informe["frames"]
    assert marcos["measuredIn"] == "RECONSTRUCTION"
    assert sorted(marcos["reachable"]) == ["ASSET_CANONICAL", "RECONSTRUCTION"]


@necesita_node
def test_no_se_afirma_una_precision_que_nadie_justifica(informe: Informe) -> None:
    """D9: escala RELATIVE y sin modelo de incertidumbre no promete nada."""
    assert informe["scale"]["claimsAbsolutePrecision"] is False


@necesita_node
def test_el_unico_aviso_es_el_de_cobertura(informe: Informe) -> None:
    """Cuatro camaras no ven el cubo entero, y eso se dice — no se esconde ni falla."""
    assert [aviso["code"] for aviso in informe["warnings"]] == ["SS-COV-001"]


def test_dos_generaciones_dan_el_mismo_paquete(tmp_path: pathlib.Path) -> None:
    """Sin esto, `expected.json` no puede afirmar nada (V4)."""
    uno = generar_cube_v1(tmp_path / "uno")
    otro = generar_cube_v1(tmp_path / "otro")
    for nombre in ("manifest.json", "mesh.ply", "sparse.ply", "images/oblicua.png"):
        assert (uno / nombre).read_bytes() == (otro / nombre).read_bytes(), nombre


def test_el_paquete_publicado_esta_sellado(paquete: pathlib.Path) -> None:
    manifest = json.loads((paquete / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["state"] == "SEALED"
    assert manifest["packageId"] == "cube-v1"
    assert len(manifest["artifacts"]) == DORADOS["recuentos"]["cube-v1"]["artifacts"]
