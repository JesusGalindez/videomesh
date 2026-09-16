"""Encargo 04, D3 — el material declarado, con sus mapas y su caso rojo.

R13 dice literalmente que el manifest de producción «todavía no declara» los
materiales: la auditoría de textura tiene su sitio y no ha tenido qué mirar. Esta
etapa cierra ese hueco desde el lado del productor: viste la pieza de `normales`
—copia su GLB y su PNG, y declara el material que los ata— para que la auditoría
de textura tenga un material que auditar.

Lo que se prueba, en orden de lo que decide:

- **El veredicto del vecino incluye lo del material**: con `materials` en el
  manifiesto, su informe trae `materialIssues: []` — que lo audite es condición de
  PASS, y un manifiesto sin materiales sale con el veredicto vacío y no auditado.
- **El caso rojo lo produce el vecino, no una comprobación de aquí.** Un material
  que apunta a una textura que no existe como artifact sale con `FAIL` y motivo
  `TEXTURA_AUSENTE` — su `auditMaterials` lo caza **sin abrir una sola imagen**, y
  una segunda copia del criterio aquí sería un segundo criterio de qué es válido.
- **Lo que copia se comprueba byte a byte**: los artefactos del asset del material
  son los mismos ficheros que produjo `normales`, con el hash de su manifiesto.
  Copiar a mano y declarar otra cosa sería la clase de contradicción que el propio
  vecino caza en otros manifiestos.
"""

import json
import math
import pathlib
import shutil
from typing import Any

import pytest

from videomesh.adapters.softsight import juicio_de_produccion
from videomesh.application.decimado import decimar
from videomesh.application.densa import importar_paquete
from videomesh.application.limpieza import limpiar
from videomesh.application.material import ETAPA, vestir
from videomesh.application.normales import GLB as GLB_NORMALES
from videomesh.application.normales import MAPA as MAPA_NORMALES
from videomesh.application.uv import cortar_y_empaquetar
from videomesh.cli.app import main
from videomesh.domain.malla import Malla
from videomesh.formatos.ply import escribir_ply_malla
from videomesh.project import activo
from videomesh.project.informe import leer_informe
from videomesh.project.sellado import publicar_paquete
from videomesh.project.store import crear_proyecto

#: Un juez que no existe: el caso rojo del `NOT_RUN`, sin desinstalar nada.
JUEZ_AUSENTE = pathlib.Path("/no/existe/production.mjs")


def _plano_con_bulto(*, divisiones: int = 48) -> Malla:
    """La misma malla de las pruebas de `normales`: es la que su mapa pasa al vecino.

    Lo que prueba esta etapa es el **material**, no el mapa — ese ya tiene su juez y
    sus casos rojos en la etapa que lo hornea. Un cubo aqui seria una trampa: con
    aristas duras y normales suavizadas, R13 rechazaria su mapa por como lo horneo
    `normales` sobre esa malla, y el fallo no diria nada del material.
    """

    vertices: list[tuple[float, float, float]] = []
    for j in range(divisiones + 1):
        for i in range(divisiones + 1):
            x = i / divisiones - 0.5
            y = j / divisiones - 0.5
            radio = math.sqrt(x * x + y * y)
            z = 0.06 * math.exp(-(radio * radio) / 0.12)
            vertices.append((x, y, z))
    triangulos: list[tuple[int, int, int]] = []
    ancho = divisiones + 1
    for j in range(divisiones):
        for i in range(divisiones):
            a = j * ancho + i
            triangulos += [(a, a + 1, a + ancho + 1), (a, a + ancho + 1, a + ancho)]
    return Malla(vertices=vertices, triangulos=triangulos)


def _proyecto_vestible(tmp_path: pathlib.Path) -> pathlib.Path:
    """La cadena hasta `normales`: lo que el material necesita para existir."""
    proyecto = tmp_path / "proyecto"
    crear_proyecto(proyecto, nombre="prueba")
    paquete = tmp_path / "densa-0001"
    with publicar_paquete(paquete, package_id="densa-0001", producer="producers/colmap") as obra:
        escribir_ply_malla(obra.raiz / "malla.ply", _plano_con_bulto())
        obra.anadir("malla.ply", identidad="malla", tipo="TRIANGLE_MESH", purely_reconstructed=True)
        obra.manifest["requiredEvidence"] = ["malla"]
    importar_paquete(proyecto, paquete, maquina="colab-t4")
    limpiar(proyecto)
    decimar(proyecto, objetivo=200)
    cortar_y_empaquetar(proyecto)
    from videomesh.application.normales import hornear

    hornear(proyecto, resolucion=256)
    return proyecto


def _informe(proyecto: pathlib.Path) -> dict[str, Any]:
    documento = leer_informe(proyecto, ETAPA)
    assert documento is not None
    return documento


def _situacion(proyecto: pathlib.Path, etapa: str) -> str:
    from videomesh.application.cadena import estado_de_la_cadena

    return str(next(p for p in estado_de_la_cadena(proyecto) if p.etapa == etapa).situacion.value)


# --- el asset, y que lo que declara es lo que hay ------------------------------


def test_el_asset_viste_lo_que_produjo_normales(tmp_path: pathlib.Path) -> None:
    """La pieza y el mapa del asset del material son los ficheros de `normales`.

    Se comprueba el hash contra **su** manifiesto, y no contra una copia de lo que
    alguien creía que copió: el vecino comprueba los hashes antes de mirar nada, y
    una copia infiel daría un asset que no es el que se audita.
    """
    proyecto = _proyecto_vestible(tmp_path)
    vestir(proyecto)

    manifiesto_de_normales = json.loads(
        (proyecto / "etapas" / "normales" / activo.ACTIVO).read_text(encoding="utf-8")
    )
    hashes_de_normales = {
        a["id"]: (a["sha256"], a["bytes"]) for a in manifiesto_de_normales["artifacts"]
    }

    directorio = proyecto / "etapas" / ETAPA
    for fichero in (directorio / GLB_NORMALES, directorio / MAPA_NORMALES):
        assert fichero.is_file()

    manifiesto = json.loads((directorio / activo.ACTIVO).read_text(encoding="utf-8"))
    por_identidad = {a["id"]: a for a in manifiesto["artifacts"]}
    assert por_identidad["maestra"]["sha256"] == hashes_de_normales["maestra"][0]
    assert por_identidad[MAPA_NORMALES]["sha256"] == hashes_de_normales[MAPA_NORMALES][0]
    # Y sus papeles: la pieza es MASTER, el mapa TEXTURE con uso NORMAL.
    assert por_identidad["maestra"]["role"] == "MASTER"
    assert por_identidad[MAPA_NORMALES]["role"] == "TEXTURE"
    assert por_identidad[MAPA_NORMALES]["usage"] == "NORMAL"


def test_el_material_apunta_con_los_id_del_manifiesto(tmp_path: pathlib.Path) -> None:
    """El material declara a quién pinta y con qué canales, en su vocabulario.

    `appliesTo` lleva la identidad **del artifact** maestra, y el canal `normal`
    apunta al id del mapa. Cualquier otro nombre sería un manifiesto que el propio
    vecino cazaria con MALLA_AUSENTE o TEXTURA_AUSENTE.
    """
    proyecto = _proyecto_vestible(tmp_path)
    vestir(proyecto)

    manifiesto = json.loads(
        (proyecto / "etapas" / ETAPA / activo.ACTIVO).read_text(encoding="utf-8")
    )
    assert len(manifiesto["materials"]) == 1
    material = manifiesto["materials"][0]
    assert material["appliesTo"] == ["maestra"]
    assert material["textures"]["normal"] == MAPA_NORMALES
    assert material["wrap"] in ("REPEAT", "CLAMP")


def test_sin_normales_la_etapa_dice_que_no_hay_nada_que_vestir(
    tmp_path: pathlib.Path,
) -> None:
    """El material necesita la pieza y el mapa: sin la etapa que los produce, no hay
    asset que vestir, y lo dice antes de escribir nada."""
    proyecto = _proyecto_vestible(tmp_path)
    shutil.rmtree(proyecto / "etapas" / "normales")
    with pytest.raises(Exception) as fallo:
        vestir(proyecto)
    assert "normales" in str(fallo.value)


# --- el veredicto del vecino ----------------------------------------------------


def test_el_veredicto_del_vecino_auditara_el_material(tmp_path: pathlib.Path) -> None:
    """Con `materials` en el manifiesto, su informe trae `materialIssues` revisado.

    La condición de PASS es que no haya issues — y que el manifiesto **tenga**
    materiales, porque un manifiesto sin ellos sale con el veredicto vacío y no
    auditado, que es exactamente el hueco que R13 señaló.
    """
    proyecto = _proyecto_vestible(tmp_path)
    vestir(proyecto)

    informe = _informe(proyecto)
    veredicto = informe["veredicto_del_vecino"]
    assert veredicto["estado"] == "MEDIDO"
    assert veredicto["certificacion"] == "PASS"
    assert veredicto["materialIssues"] == []
    # Y el material que el vecino vio es el que el manifiesto declaró.
    assert veredicto["materiales_declarados"] == 1


def test_un_material_que_apunta_a_textura_que_no_existe_lo_rechaza_el_vecino(
    tmp_path: pathlib.Path,
) -> None:
    """El caso rojo, y es el que decide si la etapa está hecha.

    El material declara un canal cuyo artifact no existe. El `FAIL` tiene que ser
    del vecino — `auditMaterials` lo caza sin abrir imágenes — y no de una
    comprobación de aquí.
    """
    proyecto = _proyecto_vestible(tmp_path)

    from videomesh.project import activo as modulo_activo
    from videomesh.project.informe import directorio_de_etapa

    directorio = directorio_de_etapa(proyecto, ETAPA)
    directorio.mkdir(parents=True, exist_ok=True)
    # La pieza y el mapa, los mismos de `normales` — el material es lo que está mal.
    for nombre in (GLB_NORMALES, MAPA_NORMALES):
        shutil.copy2(proyecto / "etapas" / "normales" / nombre, directorio / nombre)
    modulo_activo.escribir_activo(
        directorio,
        identidad="prueba·material-roto",
        productor="videomesh/material",
        artefactos=[
            activo.describir_artefacto(
                directorio, GLB_NORMALES, identidad="maestra", rol="MASTER", formato="GLB"
            ),
            activo.describir_artefacto(
                directorio, MAPA_NORMALES, identidad=MAPA_NORMALES, rol="TEXTURE", usage="NORMAL"
            ),
        ],
        destino={"preset": "material-de-trabajo", "budgets": []},
        materiales=[
            {
                "id": "material-roto",
                "appliesTo": ["maestra"],
                "textures": {"normal": "el-mapa-que-no-declare"},
                "wrap": "REPEAT",
            }
        ],
    )

    juicio = juicio_de_produccion(directorio / activo.ACTIVO)
    assert juicio["certificacion"] == "FAIL"
    assert juicio["motivo"] == "TEXTURA_AUSENTE"
    issues = juicio["informe"]["materialIssues"]
    assert issues[0]["material"] == "material-roto"
    assert issues[0]["reason"] == "TEXTURA_AUSENTE"


def test_sin_el_juez_declara_que_no_se_pudo_juzgar(tmp_path: pathlib.Path) -> None:
    """El mismo criterio de las etapas anteriores: produce y publica `NOT_RUN`."""
    proyecto = _proyecto_vestible(tmp_path)
    vestir(proyecto, herramienta_de_produccion=JUEZ_AUSENTE)

    informe = _informe(proyecto)
    veredicto = informe["veredicto_del_vecino"]
    assert veredicto["estado"] == "NOT_RUN"
    assert "production.mjs" in str(veredicto["motivo"])
    assert any(p["que"] == "veredicto_de_produccion" for p in informe["no_comprobado"])


def test_la_etapa_caduca_cuando_cambia_el_mapa(tmp_path: pathlib.Path) -> None:
    """§9 con su caso concreto: hornear otra vez deja el material citando otro mapa.

    El hash de entrada lleva el de la pieza y el del mapa, así que cambiar cualquiera
    de los dos se ve en `status` sin lanzar nada.
    """
    proyecto = _proyecto_vestible(tmp_path)
    vestir(proyecto)
    assert _situacion(proyecto, ETAPA) == "HECHA"

    from videomesh.application.normales import hornear

    hornear(proyecto, resolucion=512)
    assert _situacion(proyecto, ETAPA) == "CADUCADA"


def test_la_orden_ensena_el_material_y_su_veredicto(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """La salida de `videomesh material`: qué declara y quién lo juzgó."""
    proyecto = _proyecto_vestible(tmp_path)
    assert main(["material", str(proyecto)]) == 0
    salida = capsys.readouterr().out
    assert "material" in salida
    assert "normales" in salida
    assert "informe del vecino          PASS" in salida
