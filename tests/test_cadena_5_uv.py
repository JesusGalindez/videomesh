"""Encargo 04, C2 — el atlas de UV, y el juez que lo juzga.

La etapa corta y empaqueta, y **no escribe su propio veredicto**. Las UV las juzga la
auditoría del vecino sobre el GLB, y ese es el caso rojo de este bloque:

    un asset cuyas UV se solapan a propósito tiene que salir rechazado por su
    auditoría, no por una comprobación de aquí.

Por eso la prueba del rechazo **no** mira nuestro informe: le pasa al vecino un GLB con
las UV pisadas a propósito y comprueba que el `FAIL` viene de su auditoría, con su
motivo y sus números. Si el rechazo lo produjera código nuestro, habría dos criterios de
qué es una UV válida y el día que discrepen nadie sabría cuál manda.

Dos cosas más se prueban aquí, y las dos son de honestidad:

- **Partir no es mover.** El atlas añade vértices por las costuras y no mueve ninguno.
  Se publican los dos números juntos: cuántos vértices añadió, y la distancia de
  superficie en las dos direcciones.
- **Sin juez, `NOT_RUN`.** Si el informe del vecino no se puede ejecutar, la etapa sigue
  produciendo su GLB y declara que no se pudo juzgar. Un verde por omisión sería la
  peor de las salidas posibles.
"""

import hashlib
import json
import pathlib
from typing import Any

import pytest

from videomesh.adapters import glb
from videomesh.adapters.softsight import juicio_de_produccion
from videomesh.application.decimado import decimar
from videomesh.application.densa import importar_paquete
from videomesh.application.limpieza import limpiar
from videomesh.application.uv import ETAPA, GLB, PRODUCCION, cortar_y_empaquetar
from videomesh.cli.app import main
from videomesh.domain.malla import Malla
from videomesh.formatos.ply import escribir_ply_malla
from videomesh.project import activo
from videomesh.project.informe import leer_informe
from videomesh.project.sellado import publicar_paquete
from videomesh.project.store import crear_proyecto

#: Un juez que no existe: el caso rojo del `NOT_RUN`, sin desinstalar nada.
JUEZ_AUSENTE = pathlib.Path("/no/existe/production.mjs")

#: El suelo de ruido de `diffMeshes` de SoftSight, en fracción de la diagonal. Es suyo
#: y se lee de su fuente, no se copia con otro número.
SUELO_DE_RUIDO = 4e-16


def _cubo(centro: tuple[float, float, float] = (0.0, 0.0, 0.0), divisiones: int = 4) -> Malla:
    """Un cubo con las aristas soldadas: un solo componente y superficie de verdad."""
    n = divisiones
    vertices: list[tuple[float, float, float]] = []
    indice: dict[tuple[int, int, int], int] = {}

    def vertice(i: int, j: int, k: int) -> int:
        clave = (i, j, k)
        if clave not in indice:
            indice[clave] = len(vertices)
            vertices.append(
                (
                    centro[0] + (i / n - 0.5),
                    centro[1] + (j / n - 0.5),
                    centro[2] + (k / n - 0.5),
                )
            )
        return indice[clave]

    triangulos = []
    for eje in range(3):
        otros = [a for a in range(3) if a != eje]
        for extremo in (0, n):
            for u in range(n):
                for v in range(n):
                    anillo = []
                    for du, dv in ((u, v), (u + 1, v), (u + 1, v + 1), (u, v + 1)):
                        coordenadas = [0, 0, 0]
                        coordenadas[eje] = extremo
                        coordenadas[otros[0]] = du
                        coordenadas[otros[1]] = dv
                        anillo.append(vertice(*coordenadas))
                    triangulos += [
                        (anillo[0], anillo[1], anillo[2]),
                        (anillo[0], anillo[2], anillo[3]),
                    ]
    return Malla(vertices=vertices, triangulos=triangulos)


def _proyecto_limpio(tmp_path: pathlib.Path, malla: Malla) -> pathlib.Path:
    """Un proyecto con la malla importada y ya limpia: la entrada de la etapa `uv`."""
    proyecto = tmp_path / "proyecto"
    crear_proyecto(proyecto, nombre="prueba")
    paquete = tmp_path / "densa-0001"
    with publicar_paquete(paquete, package_id="densa-0001", producer="producers/colmap") as obra:
        escribir_ply_malla(obra.raiz / "malla.ply", malla)
        obra.anadir("malla.ply", identidad="malla", tipo="TRIANGLE_MESH", purely_reconstructed=True)
        obra.manifest["requiredEvidence"] = ["malla"]
    importar_paquete(proyecto, paquete, maquina="colab-t4")
    limpiar(proyecto)
    return proyecto


def _informe(proyecto: pathlib.Path) -> dict[str, Any]:
    documento = leer_informe(proyecto, ETAPA)
    assert documento is not None
    return documento


def _medidas(proyecto: pathlib.Path) -> dict[str, Any]:
    valores: dict[str, Any] = _informe(proyecto)["medidas"]
    return valores


# --- la lectura que el cortador necesita ---------------------------------------


def test_los_arreglos_del_proveedor_traen_la_malla_entera(tmp_path: pathlib.Path) -> None:
    """El `MeshSet` de pymeshlab tiene que seguir vivo mientras se le pide la malla.

    `current_mesh()` devuelve una **vista** sobre el objeto de C++, asi que si el
    conjunto se queda sin referencia la vista se lee vacia. Se comprobo el 2026-09-16
    sobre un cubo de 98 vertices: con el conjunto vivo, 98; sin el, 0 — y sin un error,
    que es lo que lo hace peligroso: el cortador recibiria una malla vacia y produciria
    un atlas vacio sin que nada protestara.
    """
    from videomesh.adapters import pymeshlab

    proyecto = _proyecto_limpio(tmp_path, _cubo())
    ruta = proyecto / "etapas" / "limpieza" / "malla.ply"
    vertices, caras = pymeshlab.a_arreglos(ruta)
    medidas = pymeshlab.medir(ruta)
    assert vertices.shape == (medidas.vertices, 3)
    assert caras.shape == (medidas.caras, 3)


# --- la etapa, cuando el juez está --------------------------------------------


def test_la_etapa_publica_el_glb_con_uv_y_el_asset_que_lo_declara(
    tmp_path: pathlib.Path,
) -> None:
    """Sin un fichero que lleve las coordenadas no hay nada que auditar: un PLY no las
    admite, y por eso esta etapa escribe un GLB."""
    proyecto = _proyecto_limpio(tmp_path, _cubo())
    cortar_y_empaquetar(proyecto)

    directorio = proyecto / "etapas" / ETAPA
    assert (directorio / GLB).is_file()
    assert (directorio / activo.ACTIVO).is_file()
    assert (directorio / "informe.json").is_file()

    manifiesto = json.loads((directorio / activo.ACTIVO).read_text(encoding="utf-8"))
    assert manifiesto["state"] == "SEALED"
    assert manifiesto["artifacts"][0]["role"] == "MASTER"
    assert manifiesto["artifacts"][0]["format"] == "GLB"
    # El hash del manifiesto es el del fichero que hay: el vecino lo comprueba antes de
    # mirar nada, y si no cuadra da el asset por no leído.
    glb_en_disco = (directorio / GLB).read_bytes()
    assert manifiesto["artifacts"][0]["bytes"] == len(glb_en_disco)
    assert manifiesto["artifacts"][0]["sha256"] == hashlib.sha256(glb_en_disco).hexdigest()


def test_la_etapa_publica_lo_que_produjo_y_lo_que_dice_el_vecino(
    tmp_path: pathlib.Path,
) -> None:
    """El número de islas y el veredicto, cada uno de quien lo sabe.

    Las islas las cuenta el corte —es su resultado— y la validez de las UV la dice la
    auditoría del vecino.
    """
    proyecto = _proyecto_limpio(tmp_path, _cubo())
    cortar_y_empaquetar(proyecto)

    medidas = _medidas(proyecto)
    assert int(medidas["islas"]) >= 1
    # El cubo con cuatro divisiones por lado: seis caras de 32 triangulos.
    assert int(medidas["triangulos"]) == 192
    assert int(medidas["empaquetado"]["ancho"]) > 0

    veredicto: dict[str, Any] = _informe(proyecto)["veredicto_del_vecino"]
    assert veredicto["estado"] == "MEDIDO"
    assert veredicto["certificacion"] == "PASS"
    maestra: dict[str, Any] = veredicto["maestra"]
    uv: dict[str, Any] = maestra["uv"]
    assert uv["present"] is True
    # El solape de un atlas limpio no es cero exacto: la auditoria lo mide contra una
    # rejilla, y su suelo depende del empaquetado. Lo que tiene que quedar claro es
    # que esta a ordenes de magnitud de un solape de verdad —el que se prueba abajo—.
    assert float(uv["overlapRatio"]) < 0.01
    veredictos: dict[str, str] = maestra["veredictos"]
    assert veredictos["overlap"] == "PASS"


def test_el_veredicto_publicado_es_el_del_vecino_y_su_informe_esta_al_lado(
    tmp_path: pathlib.Path,
) -> None:
    """Un veredicto citado sin su informe obliga a repetir la auditoría para comprobar
    qué decía. El informe entero se guarda junto al asset que juzgó."""
    proyecto = _proyecto_limpio(tmp_path, _cubo())
    cortar_y_empaquetar(proyecto)

    directorio = proyecto / "etapas" / ETAPA
    guardado = json.loads((directorio / PRODUCCION).read_text(encoding="utf-8"))
    veredicto: dict[str, Any] = _informe(proyecto)["veredicto_del_vecino"]

    assert veredicto["informe"] == PRODUCCION
    assert veredicto["certificacion"] == guardado["certification"]
    assert str(veredicto["comando"]).startswith("node ")


def test_el_atlas_anade_vertices_por_las_costuras_y_no_mueve_ninguno(
    tmp_path: pathlib.Path,
) -> None:
    """La medida que puede parecer una pérdida y no lo es, dicha con los dos números.

    Partir un vértice en dos por una costura cambia el recuento y no la superficie. Por
    eso se publican juntos: cuántos vértices añadió el corte, y la distancia de
    superficie en las dos direcciones —que es la del ruido de la aritmética—.
    """
    proyecto = _proyecto_limpio(tmp_path, _cubo())
    cortar_y_empaquetar(proyecto)

    medidas = _medidas(proyecto)
    assert int(medidas["vertices_despues"]) >= int(medidas["vertices_antes"])
    assert int(medidas["vertices_anadidos_por_las_costuras"]) == int(
        medidas["vertices_despues"]
    ) - int(medidas["vertices_antes"])

    for nombre in ("distancia", "distancia_contra_la_malla_medida"):
        distancia: dict[str, Any] = medidas[nombre]
        assert distancia["estado"] == "MEDIDA"
        for direccion in ("falta", "sobra"):
            datos: dict[str, float] = distancia[direccion]
            # El suelo de esta medida no es el del diff: el GLB escribe las posiciones
            # en coma flotante de 32 bits, asi que redondear al escribir deja un resto
            # del orden de 1e-13 de la diagonal —medido el 2026-09-16: 1,98e-12 sobre
            # una malla de 2.915 triangulos, con suelo del diff 1,03e-14—. Lo que la
            # prueba tiene que separar es eso de una perdida de verdad: el decimado de
            # la misma cadena, medido contra la malla medida, da 4,9e-03.
            assert datos["fraccion_de_la_diagonal"] <= 1e-9, (
                f"la distancia `{direccion}` es {datos['maximo']:.3e}, que no es el redondeo "
                "de escribir un GLB: algo movio superficie"
            )


# --- el caso rojo: quien rechaza es el vecino ---------------------------------


def _glb_con_uv_pisadas(destino: pathlib.Path) -> None:
    """Dos triángulos **sobre las mismas UV**: solape de verdad, pintado dos veces.

    No es una malla que salga de xatlas —el cortador no produce esto—, es un caso rojo
    escrito a mano para probar la puerta: si el rechazo viniera de nuestro código, la
    puerta no estaría probada. La geometría es un solo triángulo repetido, así que su
    superficie no aporta nada raro y lo único que se mide es el atlas.
    """
    glb.escribir_glb(
        destino,
        vertices=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0)],
        triangulos=[(0, 1, 2), (0, 1, 2)],
        uv=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)],
    )


def test_un_atlas_con_uv_solapadas_lo_rechaza_la_auditoria_del_vecino(
    tmp_path: pathlib.Path,
) -> None:
    """El caso rojo del bloque, y el que decide si la etapa está hecha.

    El asset se escribe con nuestro manifiesto —el mismo `destino` que declara la
    etapa, con el solape a cero— y se le pasa al vecino. El `FAIL` tiene que ser suyo.
    """
    directorio = tmp_path / "asset"
    _glb_con_uv_pisadas(directorio / GLB)
    asset = activo.escribir_activo(
        directorio,
        identidad="prueba·uv",
        productor="videomesh/uv",
        artefactos=[
            activo.describir_artefacto(
                directorio, GLB, identidad="maestra", rol="MASTER", formato="GLB"
            )
        ],
        destino={"preset": "uv-de-trabajo", "budgets": [], "uvOverlapMax": 0.0},
    )

    juicio = juicio_de_produccion(asset)
    assert juicio["certificacion"] == "FAIL"
    assert juicio["motivo"] == "UV_FUERA_DE_TOLERANCIA_OVERLAP"

    informe = juicio["informe"]
    maestra = next(m for m in informe["measurements"] if m["role"] == "MASTER")
    assert maestra["uvVerdicts"]["overlap"] == "FAIL"
    assert maestra["uv"]["overlapRatio"] > 0.9, (
        f"los dos triángulos están uno sobre el otro y el solape sale "
        f"{maestra['uv']['overlapRatio']}"
    )


def test_el_atlas_que_corta_xatlas_pasa_ese_mismo_tope(tmp_path: pathlib.Path) -> None:
    """Y el que sí produce la etapa pasa el mismo criterio: si los dos pasaran, o los
    dos fallaran, la prueba de arriba no distinguiría nada."""
    proyecto = _proyecto_limpio(tmp_path, _cubo())
    cortar_y_empaquetar(proyecto)

    veredicto: dict[str, Any] = _informe(proyecto)["veredicto_del_vecino"]
    maestra: dict[str, Any] = veredicto["maestra"]
    veredictos: dict[str, str] = maestra["veredictos"]
    assert veredictos["overlap"] == "PASS"


# --- cuando el juez no está ---------------------------------------------------


def test_sin_el_juez_la_etapa_produce_y_declara_que_no_se_pudo_juzgar(
    tmp_path: pathlib.Path,
) -> None:
    """Un verde por omisión sería la peor salida posible: se publica `NOT_RUN`."""
    proyecto = _proyecto_limpio(tmp_path, _cubo())
    cortar_y_empaquetar(proyecto, herramienta_de_produccion=JUEZ_AUSENTE)

    directorio = proyecto / "etapas" / ETAPA
    assert (directorio / GLB).is_file(), "el asset se produce igual: lo que falta es el juez"

    informe = _informe(proyecto)
    veredicto: dict[str, Any] = informe["veredicto_del_vecino"]
    assert veredicto["estado"] == "NOT_RUN"
    assert "production.mjs" in str(veredicto["motivo"])

    pendientes: list[dict[str, str]] = informe["no_comprobado"]
    assert any(p["que"] == "veredicto_de_produccion" for p in pendientes)
    assert not (directorio / PRODUCCION).exists()


# --- determinismo, caducidad y la orden ---------------------------------------


def test_la_misma_entrada_da_el_mismo_atlas(tmp_path: pathlib.Path) -> None:
    """Lo que justifica declarar la etapa `DETERMINISTA` y poder saltársela.

    Se comprueba en vez de suponerse: dos proyectos con la misma malla tienen que dar
    el mismo GLB byte a byte. Si algún día no lo dan, el determinismo del registro es
    una afirmación falsa y la etapa se estaría reutilizando por lo que dice y no por
    lo que es.
    """
    primero = _proyecto_limpio(tmp_path / "uno", _cubo())
    segundo = _proyecto_limpio(tmp_path / "dos", _cubo())
    cortar_y_empaquetar(primero)
    cortar_y_empaquetar(segundo)

    assert _informe(primero)["salidas"][0]["sha256"] == _informe(segundo)["salidas"][0]["sha256"]


def test_el_atlas_caduca_cuando_cambia_la_malla_de_trabajo(tmp_path: pathlib.Path) -> None:
    """§9 con su caso concreto: decimar otra vez deja el atlas describiendo otra malla.

    Un COMPLETE cuya entrada cambió no está hecho, está caducado, y lo decide el hash de
    la entrada —no el estado del registro—.
    """
    proyecto = _proyecto_limpio(tmp_path, _cubo())
    cortar_y_empaquetar(proyecto)
    assert _situacion(proyecto, ETAPA) == "HECHA"

    decimar(proyecto, objetivo=24)
    assert _situacion(proyecto, ETAPA) == "CADUCADA"


def test_la_orden_ensena_el_juicio_del_vecino_y_no_uno_propio(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """La salida de `videomesh uv` trae los números del vecino, con su nombre."""
    proyecto = _proyecto_limpio(tmp_path, _cubo())
    assert main(["uv", str(proyecto)]) == 0
    salida = capsys.readouterr().out
    assert "informe del vecino          PASS" in salida
    assert "uv                        solape" in salida
    assert "islas" in salida and "por las costuras" in salida


def _situacion(proyecto: pathlib.Path, etapa: str) -> str:
    from videomesh.application.cadena import estado_de_la_cadena

    return str(next(p for p in estado_de_la_cadena(proyecto) if p.etapa == etapa).situacion.value)
