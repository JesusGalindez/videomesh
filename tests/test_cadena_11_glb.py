"""Encargo 04, E3 — el GLB final, con `meshoptimizer` y KTX2 para el perfil web.

El instrumento está **comprobado**: el `gltfpack` de npm no trae BasisU — su propio
wasm lo dice: «node.js builds do not support BasisU due to lack of platform
features» — y el binario nativo v1.2 sí, medido sobre la pieza de la etapa
`normales`: produce `KHR_texture_basisu` con la imagen en `image/ktx2`.

El encargo trae un aviso, comprobado allí: el cargador del vecino **rechaza** el
GLB con `KHR_texture_basisu`, así que sobre esa variante su veredicto sale
`NOT_RUN` con ese motivo — nunca un verde por no haber mirado. La geometría se
audita sobre la variante **sin** KTX2 de la misma pasada: cambia el codificador de
texturas, no un vértice.

Lo que se prueba:

- **La pieza final es la que gltfpack produce**, y el recuento de triángulos sale
  de lo que hay en el fichero, con la cuantización que `-cc` implica.
- **Las dos variantes existen**: la auditable (sin KTX2) y la de reparto (con
  KTX2). Sus bytes difieren porque cambia el codificador de texturas; sus
  triángulos no, porque no cambia la geometría.
- **El veredicto del vecino sobre la variante auditable es el que cierra la
  etapa**, con el comando exacto citado.
"""

import pathlib
from typing import Any

import pytest

from videomesh.application.decimado import decimar
from videomesh.application.densa import importar_paquete
from videomesh.application.glb_final import ETAPA, GLB_KTX2, GLB_SIN_KTX2, empaquetar
from videomesh.application.limpieza import limpiar
from videomesh.application.normales import hornear
from videomesh.application.uv import cortar_y_empaquetar
from videomesh.cli.app import main
from videomesh.domain.malla import Malla
from videomesh.formatos.ply import escribir_ply_malla
from videomesh.project.informe import leer_informe
from videomesh.project.sellado import publicar_paquete
from videomesh.project.store import crear_proyecto


def _cubo(*, divisiones: int = 4) -> Malla:
    """Un cubo con las aristas soldadas: la malla de prueba de la cadena."""
    n = divisiones
    vertices: list[tuple[float, float, float]] = []
    indice: dict[tuple[int, int, int], int] = {}

    def vertice(i: int, j: int, k: int) -> int:
        clave = (i, j, k)
        if clave not in indice:
            indice[clave] = len(vertices)
            vertices.append((i / n - 0.5, j / n - 0.5, k / n - 0.5))
        return indice[clave]

    triangulos: list[tuple[int, int, int]] = []
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
                    triangulos.append((anillo[0], anillo[1], anillo[2]))
                    triangulos.append((anillo[0], anillo[2], anillo[3]))
    return Malla(vertices=vertices, triangulos=triangulos)


def _proyecto_base(tmp_path: pathlib.Path) -> pathlib.Path:
    """La cadena hasta `normales`: lo que el empaquetado necesita."""
    proyecto = tmp_path / "proyecto"
    crear_proyecto(proyecto, nombre="prueba")
    paquete = tmp_path / "densa-0001"
    with publicar_paquete(paquete, package_id="densa-0001", producer="producers/colmap") as obra:
        escribir_ply_malla(obra.raiz / "malla.ply", _cubo())
        obra.anadir("malla.ply", identidad="malla", tipo="TRIANGLE_MESH", purely_reconstructed=True)
        obra.manifest["requiredEvidence"] = ["malla"]
    importar_paquete(proyecto, paquete, maquina="colab-t4")
    limpiar(proyecto)
    decimar(proyecto, objetivo=192)
    cortar_y_empaquetar(proyecto)
    hornear(proyecto, resolucion=256)
    return proyecto


def _informe(proyecto: pathlib.Path) -> dict[str, Any]:
    documento = leer_informe(proyecto, ETAPA)
    assert documento is not None
    return documento


# --- el empaquetado, con sus dos variantes --------------------------------------


def test_empaqueta_las_dos_variantes(tmp_path: pathlib.Path) -> None:
    """La auditable y la de reparto, de la misma pasada.

    Sus bytes difieren — cambia el codificador de texturas — y sus triángulos no:
    `-cc` cuantiza posiciones, no recuenta geometría. Que las dos existan es lo que
    permite auditar la geometría hoy y repartir el KTX2 mañana.
    """
    proyecto = _proyecto_base(tmp_path)
    empaquetar(proyecto, destino={"preset": "material-de-trabajo", "budgets": []})

    directorio = proyecto / "etapas" / ETAPA
    assert (directorio / GLB_SIN_KTX2).is_file()
    assert (directorio / GLB_KTX2).is_file()

    informe = _informe(proyecto)
    sin_ktx2, con_ktx2 = informe["medidas"]["sin_ktx2"], informe["medidas"]["con_ktx2"]
    assert sin_ktx2["bytes"] != con_ktx2["bytes"]
    assert sin_ktx2["triangulos"] == con_ktx2["triangulos"]
    # La pieza final lleva material en su JSON, con su textura en KTX2.
    assert con_ktx2["ktx2"] is True
    assert sin_ktx2["ktx2"] is False


def test_la_variante_ktx2_declara_la_extension_que_el_vecino_no_lee(
    tmp_path: pathlib.Path,
) -> None:
    """El aviso del encargo, convertido en dato: la variante con KTX2 lleva
    `KHR_texture_basisu`, que es la que el cargador del vecino rechaza por nombre."""
    proyecto = _proyecto_base(tmp_path)
    empaquetar(proyecto, destino={"preset": "material-de-trabajo", "budgets": []})

    con_ktx2 = _informe(proyecto)["medidas"]["con_ktx2"]
    assert "KHR_texture_basisu" in con_ktx2["extensiones"]


def test_el_veredicto_del_vecino_sobre_la_variante_auditable(
    tmp_path: pathlib.Path,
) -> None:
    """La auditoría corre sobre la variante **sin** KTX2: cambia el códec, no la
    geometría. El veredicto es el del vecino, con el comando citado."""
    proyecto = _proyecto_base(tmp_path)
    empaquetar(
        proyecto,
        destino={
            "preset": "material-de-trabajo",
            "budgets": [],
            "textureMaxSize": 256,
            "texturePowerOfTwo": True,
        },
    )

    veredicto = _informe(proyecto)["veredicto_del_vecino"]
    assert veredicto["estado"] == "MEDIDO"
    assert veredicto["variante"] == GLB_SIN_KTX2
    assert str(veredicto["comando"]).startswith("node ")


def test_sin_instrumento_la_etapa_falla_diciendo_lo_que_falta(
    tmp_path: pathlib.Path,
) -> None:
    """`gltfpack` es un instrumento externo: si falta, la frontera lo dice con las
    tres partes — qué falta, para qué y cómo se consigue."""
    proyecto = _proyecto_base(tmp_path)
    import videomesh.application.glb_final as modulo

    falsa = modulo.Gltfpack
    original = falsa.binario
    falsa.binario = pathlib.Path("/no/existe/gltfpack")
    try:
        with pytest.raises(Exception) as fallo:
            empaquetar(proyecto, destino={"preset": "x", "budgets": []})
    finally:
        falsa.binario = original
    mensaje = str(fallo.value)
    assert "gltfpack" in mensaje
    assert "meshoptimizer" in mensaje  # cómo se consigue


def test_la_orden_glb_ensena_las_dos_piezas(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """La salida de `videomesh glb`: las dos variantes, y quién juzgó la auditable."""
    proyecto = _proyecto_base(tmp_path)
    assert main(["glb", str(proyecto)]) == 0
    salida = capsys.readouterr().out
    assert GLB_SIN_KTX2 in salida
    assert GLB_KTX2 in salida
    assert "informe del vecino" in salida
