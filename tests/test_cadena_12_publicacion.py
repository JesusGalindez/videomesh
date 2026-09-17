"""Encargo 04, E4 — el paquete de producción, sellado y pasado por la QA.

`publish` cierra el bloque E y es lo único de la cadena que **no** produce una pieza
más: lo que produce es el veredicto. Junta lo que las etapas anteriores publicaron,
lo sella con el destino declarado y lo pasa por la QA de SoftSight — con el informe
del validador de Khronos dentro, porque su `readiness` **no aprueba sin él**: dice
que sin un validador externo no se puede afirmar que un GLB sea un GLB.

Lo que se prueba:

- **Sale el paquete sellado**, con sus hashes leídos del disco y el manifiesto escrito
  el último: lo que declara es lo que hay, y ninguna ruta apunta fuera.
- **El veredicto es del vecino**: `PRODUCTION_READY` contra el perfil declarado, con
  su comando citado, o `UNKNOWN` con la lista de lo que falta — nunca un verde por no
  haber mirado.
- **La variante de reparto se declara no auditada.** Su cargador rechaza
  `KHR_texture_basisu`, así que va en `no_comprobado` con su motivo: se publica, viaja
  en el paquete, y su veredicto dice `NOT_RUN` en vez de callarse.
"""

import hashlib
import json
import math
import pathlib
from typing import Any

import pytest

from videomesh.application import perfiles
from videomesh.application.decimado import decimar
from videomesh.application.densa import importar_paquete
from videomesh.application.glb_final import ETAPA as ETAPA_GLB
from videomesh.application.glb_final import GLB_KTX2
from videomesh.application.limpieza import limpiar
from videomesh.application.normales import hornear
from videomesh.application.publicacion import ETAPA, publicar
from videomesh.application.uv import cortar_y_empaquetar
from videomesh.cli.app import main
from videomesh.domain.errores import ErrorDeProyecto
from videomesh.domain.malla import Malla
from videomesh.formatos.ply import escribir_ply_malla
from videomesh.project.informe import leer_informe
from videomesh.project.sellado import publicar_paquete
from videomesh.project.store import crear_proyecto


def _plano_con_bulto(*, divisiones: int = 16) -> Malla:
    """La malla de las pruebas de `normales` y `material`: su mapa pasa al vecino.

    La publicación **no** elige malla: hereda la que la cadena produjo. Pero la que
    usa esta prueba sí importa, y por eso es la de siempre: un cubo sería una trampa
    —con aristas duras y normales suavizadas su mapa de normales sale con un 12 % de
    téxeles bajo el horizonte, y el vecino lo rechaza con razón—, y aquí lo que se
    prueba es el **paquete**, no cómo hornea la etapa anterior.
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


def _proyecto(tmp_path: pathlib.Path, *, hasta_glb: bool = True) -> pathlib.Path:
    """La cadena hasta `glb`: lo que la publicación necesita que exista."""
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
    hornear(proyecto, resolucion=256)
    if hasta_glb:
        from videomesh.application.glb_final import empaquetar

        empaquetar(proyecto, destino=perfiles.destino_declarado("hero"))
    return proyecto


def _informe(proyecto: pathlib.Path) -> dict[str, Any]:
    documento = leer_informe(proyecto, ETAPA)
    assert documento is not None
    return documento


# --- el paquete sellado, y el veredicto del vecino ------------------------------


def test_publica_el_paquete_sellado_y_el_vecino_lo_aprueba(tmp_path: pathlib.Path) -> None:
    """`PRODUCTION_READY` contra el perfil declarado, con los hashes leídos del disco.

    Lo que el manifiesto declara es lo que hay: se recomputa cada `sha256` sobre el
    fichero del paquete y se compara. Un paquete que declara lo que creía pesar es la
    clase de contradicción que su propia puerta caza.
    """
    proyecto = _proyecto(tmp_path)
    publicar(proyecto, destino=perfiles.destino_de_reparto("web"))

    paquete = proyecto / "publicacion" / "web"
    manifiesto = json.loads((paquete / "asset.json").read_text(encoding="utf-8"))
    assert manifiesto["state"] == "SEALED"
    assert manifiesto["documentType"] == "softsight.production-asset"
    assert manifiesto["target"]["preset"] == "web"
    assert manifiesto["materials"][0]["appliesTo"] == ["maestra"]

    for artefacto in manifiesto["artifacts"]:
        contenido = (paquete / artefacto["path"]).read_bytes()
        assert artefacto["bytes"] == len(contenido)
        assert artefacto["sha256"] == hashlib.sha256(contenido).hexdigest()

    informe = _informe(proyecto)
    veredicto = informe["medidas"]["veredicto"]
    assert veredicto["estado"] == "PRODUCTION_READY"
    assert veredicto["falta"] == []
    assert informe["medidas"]["validacion_externa"]["errores"] == 0
    assert informe["medidas"]["validacion_externa"]["proveedor"] == "khronos-gltf-validator"
    # Y el vecino **dice** haberla leído: sin esto, un `--external` que no llegara
    # saldría igual de verde, y la aprobación estaría apoyada en nada.
    leida = veredicto["validacion_leida_por_el_vecino"]
    assert leida is not None
    assert leida["provider"] == "khronos-gltf-validator"
    assert leida["errors"] == 0


def test_sin_lo_que_el_destino_exige_el_veredicto_es_unknown_con_su_lista(
    tmp_path: pathlib.Path,
) -> None:
    """Un destino mudo no aprueba: `UNKNOWN` y la lista de lo que falta, con su motivo.

    Es la regla de R15 en su forma más incómoda —el asset está bien y no se puede
    aprobar porque nadie declaró contra qué—, y por eso el veredicto no la esconde.
    """
    proyecto = _proyecto(tmp_path)
    publicar(proyecto, destino={"preset": "mudo", "budgets": []})

    veredicto = _informe(proyecto)["medidas"]["veredicto"]
    assert veredicto["estado"] == "UNKNOWN"
    falta = {entrada["id"]: entrada for entrada in veredicto["falta"]}
    assert "tope-de-textura" in falta
    assert falta["tope-de-textura"]["motivo"] == "EL_DESTINO_NO_LO_DECLARA"


def test_la_variante_ktx2_se_declara_no_auditada(tmp_path: pathlib.Path) -> None:
    """La que el cargador del vecino no abre **viaja** y **se declara**.

    No se puede declarar como artifact —su lector revienta el informe entero en vez
    de dar un `NOT_RUN`—, así que se publica aparte: el paquete la lleva, y el
    informe dice por qué su veredicto no existe.
    """
    proyecto = _proyecto(tmp_path)
    publicar(proyecto, destino=perfiles.destino_de_reparto("web"))

    assert (proyecto / "publicacion" / "web" / GLB_KTX2).is_file()
    pendientes = {
        entrada["que"]: entrada["motivo"] for entrada in _informe(proyecto)["no_comprobado"]
    }
    assert GLB_KTX2 in pendientes
    assert "KHR_texture_basisu" in pendientes[GLB_KTX2]
    assert "NOT_RUN" in pendientes[GLB_KTX2]


def test_sin_la_etapa_glb_no_hay_nada_que_publicar(tmp_path: pathlib.Path) -> None:
    """La publicación no inventa la pieza: la lee del informe de `glb`."""
    proyecto = _proyecto(tmp_path, hasta_glb=False)
    with pytest.raises(ErrorDeProyecto) as fallo:
        publicar(proyecto, destino=perfiles.destino_de_reparto("web"))
    assert ETAPA_GLB in str(fallo.value)


def test_el_destino_que_no_existe_dice_los_que_hay() -> None:
    """Un destino no medido no se declara: el error nombra los que sí."""
    with pytest.raises(Exception) as fallo:
        perfiles.destino_de_reparto("consola")
    assert "web" in str(fallo.value)


def test_la_orden_publish_ensena_el_veredicto_y_el_comando(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`videomesh publish --destino web`, tal y como lo pide el encargo."""
    proyecto = _proyecto(tmp_path)
    assert main(["publish", str(proyecto), "--destino", "web"]) == 0
    salida = capsys.readouterr().out
    assert "PRODUCTION_READY" in salida
    assert GLB_KTX2 in salida
    assert "informe del vecino" in salida
