"""D3 y D4 — V10, D23: las tres comparaciones, y R0-B.

    SoftSight <-> expected.json      VideoMesh <-> expected.json      SoftSight <-> VideoMesh

No basta `SoftSight == VideoMesh`: los dos pueden implementar el mismo error. Y no
basta el oraculo solo: lo escribe este repositorio, asi que por si mismo solo
probaria que nada ha cambiado. Hacen falta las tres.

Las tolerancias van **declaradas, no supuestas**:

    recuentos de vertices y triangulos        exactos
    caja envolvente tras normalizar el marco  1e-6, que es a lo que se redondea
    camaras registradas                       exactas

La fila de la caja es la que mas engana. Sobre `cube-v1` la normalizacion es la
identidad, asi que **una implementacion que ignore el grafo entero acierta**. Por
eso los casos de `normalizacion` de `package-parity-v1` no la usan: rotan treinta
grados y trasladan, y uno exige componer dos aristas en orden.
"""

import json
import pathlib
import shutil
import subprocess
from typing import Any

import pytest

from videomesh.application.cube_v1 import generar_cube_v1
from videomesh.application.expected import expected_generado, medir_cube_v1, normalizar_caja
from videomesh.contracts.generacion import ESQUEMAS
from videomesh.domain.malla import cubo_unidad

CONSUMIDOR = ESQUEMAS.parent / "tools" / "reconstruction.mjs"
PARIDAD = json.loads((ESQUEMAS / "fixtures" / "package-parity-v1.json").read_text())

#: Tolerancia de la fila 2, declarada: los dorados vienen a seis decimales.
TOLERANCIA_CAJA = 1e-6

necesita_node = pytest.mark.skipif(
    shutil.which("node") is None or not CONSUMIDOR.exists(),
    reason="hace falta node y el consumidor de SoftSight",
)


@pytest.fixture(scope="module")
def paquete(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    return generar_cube_v1(tmp_path_factory.mktemp("paridad") / "cube-v1")


@pytest.fixture(scope="module")
def afirmado() -> dict[str, Any]:
    documento: dict[str, Any] = json.loads(expected_generado())
    return documento


@pytest.fixture(scope="module")
def medido(paquete: pathlib.Path) -> dict[str, Any]:
    return medir_cube_v1(paquete)


@pytest.fixture(scope="module")
def informe(paquete: pathlib.Path) -> dict[str, Any]:
    if shutil.which("node") is None or not CONSUMIDOR.exists():
        pytest.skip("hace falta node y el consumidor de SoftSight")
    salida = subprocess.run(
        ["node", str(CONSUMIDOR), "inspect", str(paquete / "manifest.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert salida.returncode == 0, salida.stderr[-2000:]
    devuelto: dict[str, Any] = json.loads(salida.stdout)
    return devuelto


# --- fila 1: recuentos, exactos ---------------------------------------------


def test_recuentos_videomesh_contra_el_oraculo(
    medido: dict[str, Any], afirmado: dict[str, Any]
) -> None:
    assert medido["recuentos"] == afirmado["recuentos"]


@necesita_node
def test_recuentos_softsight_contra_el_oraculo(
    informe: dict[str, Any], afirmado: dict[str, Any]
) -> None:
    malla = afirmado["recuentos"]["malla"]
    medida = informe["measurements"][0]
    assert medida["vertices"] == malla["vertices"]
    assert medida["triangles"] == malla["triangulos"]
    assert medida["vertices"] - medida["duplicatePositions"] == malla["verticesSoldados"]


@necesita_node
def test_recuentos_softsight_contra_videomesh(
    informe: dict[str, Any], medido: dict[str, Any]
) -> None:
    """La tercera columna, que es la que a D23 le faltaba: dos implementaciones."""
    malla = medido["recuentos"]["malla"]
    medida = informe["measurements"][0]
    assert medida["vertices"] == malla["vertices"]
    assert medida["triangles"] == malla["triangulos"]
    assert len(informe["evidence"]["artifacts"]) == medido["recuentos"]["artifacts"]


# --- fila 2: caja tras normalizar el marco ----------------------------------


def _cerca(uno: list[float], otro: list[float]) -> bool:
    return all(abs(a - b) <= TOLERANCIA_CAJA for a, b in zip(uno, otro, strict=True))


def test_caja_videomesh_contra_el_oraculo(medido: dict[str, Any], afirmado: dict[str, Any]) -> None:
    for marco in ("malla", "nube", "enASSET_CANONICAL"):
        assert _cerca(medido["caja"][marco]["min"], afirmado["caja"][marco]["min"]), marco
        assert _cerca(medido["caja"][marco]["max"], afirmado["caja"][marco]["max"]), marco


@necesita_node
def test_caja_softsight_contra_el_oraculo(
    informe: dict[str, Any], afirmado: dict[str, Any]
) -> None:
    medida = informe["measurements"][0]
    assert _cerca(medida["boundingBoxMin"], afirmado["caja"]["malla"]["min"])
    assert _cerca(medida["boundingBoxMax"], afirmado["caja"]["malla"]["max"])


@necesita_node
def test_caja_softsight_contra_videomesh(informe: dict[str, Any], medido: dict[str, Any]) -> None:
    medida = informe["measurements"][0]
    assert _cerca(medida["boundingBoxMin"], medido["caja"]["malla"]["min"])
    assert _cerca(medida["boundingBoxMax"], medido["caja"]["malla"]["max"])


@pytest.mark.parametrize(
    "caso", [pytest.param(c, id=c["caso"]) for c in PARIDAD["caja"]["normalizacion"]]
)
def test_la_caja_normalizada_cae_en_los_valores_dorados(caso: dict[str, Any]) -> None:
    """Lo que separa leer el grafo de ignorarlo. Sobre el cubo solo, la fila no distingue nada."""
    obtenida = normalizar_caja(cubo_unidad().vertices, caso["transforms"], caso["a"], caso["de"])
    if caso["caja"] is None:
        # Sin camino, `None` y no la identidad. Un grafo incompleto no se arregla
        # suponiendo que seguramente son el mismo marco (D11).
        assert obtenida is None
        return
    assert obtenida is not None
    assert _cerca(obtenida["min"], caso["caja"]["min"])
    assert _cerca(obtenida["max"], caso["caja"]["max"])


def test_ignorar_el_grafo_no_cae_en_los_dorados() -> None:
    """La primera mutacion que D23 nombra: sin ella, la fila 2 la pasa cualquiera."""
    caso = PARIDAD["caja"]["normalizacion"][0]
    sin_mirar = normalizar_caja(cubo_unidad().vertices, [], "RECONSTRUCTION", "RECONSTRUCTION")
    assert sin_mirar is not None
    assert not _cerca(sin_mirar["min"], caso["caja"]["min"])


def test_componer_al_reves_no_cae_en_los_dorados() -> None:
    """La segunda: los dos tramos son rigidos y ninguno conmuta con el otro."""
    caso = PARIDAD["caja"]["normalizacion"][1]
    al_reves = [
        {**arista, "from": arista["to"], "to": arista["from"]} for arista in caso["transforms"]
    ]
    obtenida = normalizar_caja(cubo_unidad().vertices, al_reves, caso["a"], caso["de"])
    assert obtenida is not None
    assert not _cerca(obtenida["min"], caso["caja"]["min"])


# --- fila 3: camaras registradas, exactas -----------------------------------


def test_camaras_videomesh_contra_el_oraculo(
    medido: dict[str, Any], afirmado: dict[str, Any]
) -> None:
    assert medido["camaras"] == afirmado["camaras"]


@necesita_node
def test_camaras_softsight_contra_el_oraculo(
    informe: dict[str, Any], afirmado: dict[str, Any]
) -> None:
    assert informe["cameras"]["declared"] == len(afirmado["camaras"])
    assert informe["cameras"]["withImage"] == len(afirmado["camaras"])


@necesita_node
def test_camaras_softsight_contra_videomesh(
    informe: dict[str, Any], medido: dict[str, Any]
) -> None:
    assert informe["cameras"]["declared"] == len(medido["camaras"])


# --- fila 4: proyeccion, contra la silueta que se pinto de verdad -----------


@pytest.mark.parametrize("camara", ["frontal", "lateral", "superior", "oblicua"])
def test_la_proyeccion_cae_donde_el_rasterizador_pinto(
    camara: str, afirmado: dict[str, Any]
) -> None:
    """La comprobacion que no depende de ninguna formula: se mira la imagen.

    Los ocho vertices proyectados tienen que caer dentro de la silueta que el
    rasterizador pinto, y su caja tiene que ser la de esa silueta. Si la formula
    de proyeccion y el render discreparan, el CameraSet estaria describiendo unos
    pixeles que no son los suyos — que es el error que SoftSight encontro asi.
    """
    from videomesh.application.cube_v1 import FONDO, LADO, render_de
    from videomesh.domain.camera import proyectar
    from videomesh.domain.malla import esquinas_del_cubo

    pixeles = render_de(camara)
    ocupados = [i for i, p in enumerate(pixeles) if p != FONDO]
    silueta = (
        min(i % LADO for i in ocupados),
        min(i // LADO for i in ocupados),
        max(i % LADO for i in ocupados),
        max(i // LADO for i in ocupados),
    )

    from videomesh.application.cube_v1 import CAMARAS

    pose = next(c for c in CAMARAS if c["id"] == camara)
    proyectados = [proyectar(pose, v) for v in esquinas_del_cubo()]
    caja = (
        min(p.x for p in proyectados),
        min(p.y for p in proyectados),
        max(p.x for p in proyectados),
        max(p.y for p in proyectados),
    )

    # Lo que tiene que cumplirse es una contencion, no una igualdad: el render no
    # puede pintar **fuera** de la envolvente de los vertices proyectados. Un pixel
    # de holgura por la discretizacion.
    assert silueta[0] >= caja[0] - 1.0
    assert silueta[1] >= caja[1] - 1.0
    assert silueta[2] <= caja[2] + 1.0
    assert silueta[3] <= caja[3] + 1.0

    # Y al reves con mas holgura, porque el muestreo es por centro de pixel: una
    # esquina puntiaguda puede no cubrir ningun centro y quedarse sin pintar. En la
    # vista oblicua pasa, y son 1,9 pixeles.
    assert all(abs(a - b) <= 2.0 for a, b in zip(silueta, caja, strict=True)), (silueta, caja)


# --- D4: R0-B -------------------------------------------------------------


@necesita_node
def test_r0_b(informe: dict[str, Any], medido: dict[str, Any], afirmado: dict[str, Any]) -> None:
    """Las tres comparaciones pasan sobre el cube-v1 de VideoMesh. Eso es R0-B."""
    assert informe["execution"] == "COMPLETE"
    assert informe["certification"] == "PASS"
    assert medido["recuentos"] == afirmado["recuentos"]
    assert informe["measurements"][0]["triangles"] == afirmado["recuentos"]["malla"]["triangulos"]
    assert informe["cameras"]["declared"] == len(medido["camaras"])
