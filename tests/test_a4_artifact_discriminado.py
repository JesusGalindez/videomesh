"""A4 — D21: `purelyReconstructed` requerida en TRIANGLE_MESH, prohibida en POINT_CLOUD.

Los cuatro casos estan fijados en el contrato desde el 2026-08-12. No es un campo
opcional con valor por omision: una nube de puntos no tiene superficie, asi que
ahi el campo no es que falte, es que **esta prohibido**.

Y el mensaje importa tanto como el veredicto. La nota de implementacion de D21
—que del otro lado «resulto ser el trabajo»— dice que un `anyOf` sin discriminar
da «no coincide con ninguna forma», que es correcto e inutil: hay que mirar el
literal del tipo primero y comprobar solo esa alternativa.
"""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from videomesh.contracts.generacion import ESQUEMAS
from videomesh.contracts.modelos import ReconstructionPackage

MANIFEST = json.loads(
    (ESQUEMAS.parent / "artifacts" / "cube-v1" / "manifest.json").read_text(encoding="utf-8")
)


def _con_artifacts(*artifacts: dict[str, Any]) -> dict[str, Any]:
    return dict(MANIFEST, artifacts=list(artifacts))


MALLA = {
    "id": "mesh",
    "type": "TRIANGLE_MESH",
    "path": "mesh.ply",
    "bytes": 626,
    "sha256": "b9" * 32,
    "purelyReconstructed": True,
}
NUBE = {
    "id": "sparse",
    "type": "POINT_CLOUD",
    "path": "sparse.ply",
    "bytes": 239,
    "sha256": "4b" * 32,
}


def test_malla_con_true_es_valida() -> None:
    ReconstructionPackage.model_validate(_con_artifacts(MALLA))


def test_malla_con_false_es_valida() -> None:
    """`false` no es un fallo: es lo que se emite cuando no se puede demostrar `true`."""
    ReconstructionPackage.model_validate(_con_artifacts({**MALLA, "purelyReconstructed": False}))


def test_malla_sin_el_campo_es_invalida_por_esquema() -> None:
    sin_campo = {k: v for k, v in MALLA.items() if k != "purelyReconstructed"}
    with pytest.raises(ValidationError) as capturado:
        ReconstructionPackage.model_validate(_con_artifacts(sin_campo))
    (fallo,) = capturado.value.errors()
    assert fallo["type"] == "missing"
    assert fallo["loc"][-1] == "purelyReconstructed"


def test_nube_de_puntos_con_el_campo_es_invalida_porque_esta_prohibido() -> None:
    with pytest.raises(ValidationError) as capturado:
        ReconstructionPackage.model_validate(_con_artifacts({**NUBE, "purelyReconstructed": True}))
    (fallo,) = capturado.value.errors()
    assert fallo["type"] == "extra_forbidden"
    assert fallo["loc"][-1] == "purelyReconstructed"


def test_un_tipo_que_no_existe_dice_cuales_hay() -> None:
    """El quinto caso, que sale gratis: un fallo de forma no le dice a nadie que escribir."""
    with pytest.raises(ValidationError) as capturado:
        ReconstructionPackage.model_validate(_con_artifacts({**MALLA, "type": "MESH"}))
    (fallo,) = capturado.value.errors()
    assert fallo["type"] == "union_tag_invalid"
    for admitido in ("TRIANGLE_MESH", "POINT_CLOUD", "IMAGE", "DEPTH_MAP"):
        assert admitido in fallo["msg"]


def test_el_error_senala_el_artifact_exacto_y_no_el_paquete() -> None:
    """Con cuatro artifacts, «el paquete esta mal» obliga a buscarlo a mano."""
    sin_campo = {k: v for k, v in MALLA.items() if k != "purelyReconstructed"}
    with pytest.raises(ValidationError) as capturado:
        ReconstructionPackage.model_validate(_con_artifacts(NUBE, NUBE, sin_campo))
    (fallo,) = capturado.value.errors()
    assert fallo["loc"][:2] == ("artifacts", 2)
