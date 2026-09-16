"""Encargo 04, E1 — los perfiles de destino, escritos con sus números medidos.

Un asset «bueno» no existe en abstracto: existe bueno para web o bueno para juego, y
son topes distintos. Los dos primeros perfiles **no se inventan: están medidos** —
el 2026-09-15, sobre un GLB de Hunyuan3D de 88,6 MB y 1.500.086 triángulos, con
`gltfpack` 1.2 binario nativo:

    hero    90.004 triángulos · KTX2 2048² · 4,08 MB · distancia 0,089 % de la diagonal
    fondo   23.288 triángulos · KTX2 1024² · 0,72 MB

Lo que se prueba, en orden de lo que decide:

- **Los perfiles existen, se llaman por su nombre y dicen lo que se midió.** Cambiar
  un número de estos es cambiar un presupuesto que alguien midió, y tiene que saltar.
- **Encajan con el esquema del vecino**: se validan contra el modelo que él lee, no
  contra una copia.
- **La regla de R15, vista en el vecino y no contada**: un destino que no declara
  nada no obtiene PRODUCTION_READY — su `readiness` dice `UNKNOWN` con
  `tope-de-textura: NOT_RUN · EL_DESTINO_NO_LO_DECLARA`. Es la razón de ser de este
  módulo: los topes tienen que estar declarados, y aquí es donde viven.
"""

import pathlib
import shutil
from typing import Any

import pytest

from videomesh.adapters import glb
from videomesh.adapters.softsight import juicio_de_produccion
from videomesh.application.perfiles import PERFILES, destino_declarado, perfil_de
from videomesh.contracts.modelos import ProductionAsset
from videomesh.project import activo

# --- los perfiles, y que dicen lo que se midió ---------------------------------


def test_los_dos_perfiles_estan_y_se_llaman_por_su_nombre() -> None:
    """Hero y fondo, y nadie más: un perfil no medido no se declara."""
    assert set(PERFILES) == {"hero", "fondo"}


def test_hero_declara_los_numeros_que_se_midieron() -> None:
    """Los del encargo, medidos el 2026-09-15 sobre el Hunyuan3D.

    Un presupuesto editado a mano sin medir de nuevo es una promesa nueva disfrazada
    de medida — esta prueba la cuesta cambiarla sin querer.
    """
    hero = perfil_de("hero")
    presupuestos = {b["name"]: b["max"] for b in hero["budgets"]}
    assert presupuestos["triangulos"] == 90_004
    assert hero["textureMaxSize"] == 2048
    assert hero["texturePowerOfTwo"] is True


def test_fondo_declara_los_suyos() -> None:
    """El fondo es el segundo perfil medido: menos de la sexta parte de triángulos."""
    fondo = perfil_de("fondo")
    presupuestos = {b["name"]: b["max"] for b in fondo["budgets"]}
    assert presupuestos["triangulos"] == 23_288
    assert fondo["textureMaxSize"] == 1024
    assert fondo["texturePowerOfTwo"] is True


def test_los_presupuestos_usan_el_vocabulario_del_vecino() -> None:
    """Cada presupuesto con nombre, unidad y tope — lo que `evaluateBudgets` lee.

    Un recuento declarado `RELATIVE_TO_DIAGONAL` el vecino lo rechaza por su nombre
    con `UNIDAD_DE_PRESUPUESTO_MAL_DECLARADA`: la unidad no es decoración.
    """
    for perfil in PERFILES.values():
        for presupuesto in perfil["budgets"]:
            assert presupuesto["units"] in ("ABSOLUTE", "RELATIVE_TO_DIAGONAL")


def test_un_perfil_encaja_en_el_esquema_del_vecino() -> None:
    """El `target` del perfil se valida con el modelo que el vecino lee.

    Si su esquema crece o cambia, esta validación avisa aquí y no en su puerta con
    un «no encaja» que no dice qué campo.
    """
    for nombre, perfil in PERFILES.items():
        documento = {
            "documentType": "softsight.production-asset",
            "contractVersion": "0.0.0-test",
            "assetId": f"prueba·{nombre}",
            "state": "SEALED",
            "producer": {"name": "videomesh/test", "version": "0"},
            "artifacts": [],
            "target": perfil,
        }
        ProductionAsset.model_validate(documento)


def test_un_perfil_que_no_existe_dice_los_que_hay() -> None:
    """El error nombra los disponibles: el que integra no tiene que ir a buscarlos."""
    with pytest.raises(Exception) as fallo:
        perfil_de("juego")
    assert "hero" in str(fallo.value)
    assert "fondo" in str(fallo.value)


# --- la regla de R15, comprobada contra el vecino ------------------------------


def _asset_con_textura_y_destino(directorio: pathlib.Path, destino: dict[str, Any]) -> pathlib.Path:
    """Un asset con una malla y una textura, con el destino que se le pase.

    El mapa es un PNG mínimo en el vocabulario del vecino: con `usage: NORMAL`, R13
    lo audita; lo que importa aquí es que **hay** textura, que es lo que dispara el
    `tope-de-textura` del readiness.
    """
    directorio.mkdir(parents=True, exist_ok=True)
    glb.escribir_glb(
        directorio / "malla.glb",
        vertices=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
        triangulos=[(0, 1, 2)],
        uv=[(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)],
    )
    # Un PNG de 8x8, potencia de dos: basta para que el vecino lo decodifique.
    png = pathlib.Path("/tmp/demo-normales/proyecto/etapas/normales/normales.png")
    if not png.is_file():  # pragma: no cover - la demo puede no estar
        pytest.skip("no hay PNG de referencia en /tmp")
    shutil.copy2(png, directorio / "normales.png")

    return activo.escribir_activo(
        directorio,
        identidad="prueba·destino",
        productor="videomesh/test",
        artefactos=[
            activo.describir_artefacto(
                directorio, "malla.glb", identidad="maestra", rol="MASTER", formato="GLB"
            ),
            activo.describir_artefacto(
                directorio, "normales.png", identidad="normales.png", rol="TEXTURE", usage="NORMAL"
            ),
        ],
        destino=destino,
        materiales=[
            {
                "id": "material-de-prueba",
                "appliesTo": ["maestra"],
                "textures": {"normal": "normales.png"},
                "wrap": "REPEAT",
            }
        ],
    )


def test_un_destino_que_no_declara_nada_no_esta_listo(tmp_path: pathlib.Path) -> None:
    """La regla que justifica este módulo, dicha por el vecino.

    El asset trae textura y el destino declara **nada**: su readiness no dice PASS —
    dice que el tope de textura no está declarado, y un asset sin juzgar no está
    listo. Sin perfiles declarados, el asset más vacío sería el más listo.
    """
    asset = _asset_con_textura_y_destino(
        tmp_path / "sin-nada", {"preset": "sin-nada", "budgets": []}
    )
    juicio = juicio_de_produccion(asset)
    readiness = juicio["informe"]["readiness"]
    assert readiness["verdict"] == "UNKNOWN"
    motivos = {c["id"]: (c["state"], c.get("reason")) for c in readiness["checks"]}
    assert motivos["tope-de-textura"] == ("NOT_RUN", "EL_DESTINO_NO_LO_DECLARA")


def test_un_destino_que_declara_los_topes_de_su_perfil_deja_de_tener_huecos(
    tmp_path: pathlib.Path,
) -> None:
    """El mismo asset con el destino del perfil: el tope de textura pasa a juzgarse.

    Es la diferencia que E1 trae: con el perfil declarado, la lista de lo que falta
    se acorta — y lo que queda sin declarar son las exigencias que el asset no tiene,
    que el vecino marca `NOT_DECLARED · NO_APLICA_A_ESTE_ASSET` y no son hueco.
    """
    destino = destino_declarado("hero")
    asset = _asset_con_textura_y_destino(tmp_path / "con-perfil", destino)
    juicio = juicio_de_produccion(asset)
    readiness = juicio["informe"]["readiness"]
    motivos = {c["id"]: c["state"] for c in readiness["checks"]}
    assert motivos["tope-de-textura"] == "PASS"
    # Y los que no aplican no cuentan como hueco: el asset no trae LOD ni proxy.
    assert motivos["tope-de-silueta"] == "NOT_DECLARED"
