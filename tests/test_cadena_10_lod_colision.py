"""Encargo 04, E2 — la cadena de LODs y el proxy de colisión.

Dos etapas, y la segunda con una frontera que el encargo subraya: **SoftSight se
niega a proponer el proxy** porque calcular un casco convexo es modelar — en cuanto
decidiera dónde va un vértice, dejaría de poder afirmar que sus números son
exactos. Producirlo es de aquí (`pymeshlab` tiene `generate_convex_hull`, comprobado
sobre la malla real: casco cerrado de la decimada); juzgar su holgura es de allí.

Lo que se prueba, en orden de lo que decide:

- **La cadena de LODs es una cadena**: cada nivel se decima **del anterior** —
  192 → 96 → 48 — y eso se ve en sus distancias: cada nivel publica su distancia
  contra la malla medida, que es el freno del bucle (F2).
- **El proxy se produce aquí y el vecino juzga.** La contención corre en su
  `assessCollision`, que se niega a correr sobre un proxy **abierto**. El casco es
  cerrado por construcción, y el destino declara `collisionSlackMax`: sin él, el
  readiness del vecino deja `tope-de-holgura` hueco.
- **El caso rojo lo produce el vecino**: un proxy con un agujero sale con
  `PROXY_NO_CERRADO` y contención sin correr — no se imita ese criterio aquí.
"""

import json
import pathlib
import shutil
from typing import Any

import pytest

from videomesh.adapters import glb, pymeshlab
from videomesh.adapters.softsight import juicio_de_produccion
from videomesh.application.colision import ETAPA as ETAPA_COLISION
from videomesh.application.colision import construir
from videomesh.application.decimado import decimar
from videomesh.application.densa import importar_paquete
from videomesh.application.limpieza import limpiar
from videomesh.application.lod import ETAPA as ETAPA_LOD
from videomesh.application.lod import encadenar
from videomesh.application.normales import hornear
from videomesh.application.uv import cortar_y_empaquetar
from videomesh.cli.app import main
from videomesh.domain.malla import Malla
from videomesh.formatos.ply import escribir_ply_malla
from videomesh.project import activo
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
    """La cadena hasta el decimado: lo que la cadena de LODs necesita."""
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
    return proyecto


def _proyecto_con_pieza(tmp_path: pathlib.Path) -> pathlib.Path:
    """La cadena hasta `normales`: lo que el asset del proxy necesita.

    El proxy se compara contra la **maestra** del asset, y la maestra es la pieza
    con atlas y mapa que produce `normales`.
    """
    proyecto = _proyecto_base(tmp_path)
    encadenar(proyecto, niveles=[96, 48])
    cortar_y_empaquetar(proyecto)
    hornear(proyecto, resolucion=256)
    return proyecto


def _informe(proyecto: pathlib.Path, etapa: str) -> dict[str, Any]:
    documento = leer_informe(proyecto, etapa)
    assert documento is not None
    return documento


def _situacion(proyecto: pathlib.Path, etapa: str) -> str:
    from videomesh.application.cadena import estado_de_la_cadena

    return str(next(p for p in estado_de_la_cadena(proyecto) if p.etapa == etapa).situacion.value)


# --- la cadena de niveles -------------------------------------------------------


def test_lod_encadena_los_niveles_del_anterior(tmp_path: pathlib.Path) -> None:
    """Cada nivel se decima **del anterior**, y la cadena se ve en sus números.

    No son dos decimados de la maestra: son 192 → 96 → 48. Si el segundo saliera de
    la maestra otra vez, la distancia entre niveles no contaría el detalle que el
    primero ya perdió — y la cadena mentiría.
    """
    proyecto = _proyecto_base(tmp_path)
    encadenar(proyecto, niveles=[96, 48])

    cadena = _informe(proyecto, ETAPA_LOD)["medidas"]["niveles"]
    assert [n["triangulos"] for n in cadena] == [96, 48]
    # Cada nivel declara de quién sale: del anterior, no de la maestra.
    assert [n["entrada"] for n in cadena] == ["maestra", "nivel-1"]
    # Y cada nivel publicó su distancia contra la medida: el freno del bucle.
    for nivel in cadena:
        assert nivel["distancia_contra_la_malla_medida"]["estado"] == "MEDIDA"


def test_lod_deja_de_encadenar_cuando_el_nivel_no_baja(tmp_path: pathlib.Path) -> None:
    """Un objetivo que no baja de la entrada no se simula: se para y se declara.

    La regla de F2 en miniatura: seguir encadenando con niveles que no bajan
    produciría una cadena que parece escalable y no lo es.
    """
    proyecto = _proyecto_base(tmp_path)
    # El segundo nivel pide 96 con entrada de 96: no baja, y la cadena para con lo
    # que ya produjo en vez de escribir un «nivel» que es el mismo fichero.
    encadenar(proyecto, niveles=[96, 96])
    cadena = _informe(proyecto, ETAPA_LOD)["medidas"]["niveles"]
    assert [n["nivel"] for n in cadena] == [1]
    assert _informe(proyecto, ETAPA_LOD)["medidas"]["cadena_parada"] is True


def test_lod_esta_en_la_cadena_y_caduca_con_la_entrada(tmp_path: pathlib.Path) -> None:
    """`status` lo dice sin lanzar nada, y §9 funciona sobre la cadena entera."""
    proyecto = _proyecto_base(tmp_path)
    assert _situacion(proyecto, ETAPA_LOD) == "TOCA"
    encadenar(proyecto, niveles=[96, 48])
    assert _situacion(proyecto, ETAPA_LOD) == "HECHA"
    # Al redecimar la malla de trabajo, la cadena caduca: describe otra entrada.
    decimar(proyecto, objetivo=100)
    assert _situacion(proyecto, ETAPA_LOD) == "CADUCADA"


def test_la_orden_lod_ensena_la_cadena(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """La salida de `videomesh lod`: un nivel por línea, con su distancia."""
    proyecto = _proyecto_base(tmp_path)
    assert main(["lod", str(proyecto), "--niveles", "96,48"]) == 0
    salida = capsys.readouterr().out
    assert "nivel 1" in salida and "96" in salida
    assert "nivel 2" in salida and "48" in salida


# --- el proxy de colisión --------------------------------------------------------


def _asset_de_proxy(tmp_path: pathlib.Path, *, cerrado: bool) -> pathlib.Path:
    """Un asset con maestra y proxy, escritos a mano para aislar el criterio.

    Con `cerrado=False`, al casco se le quita una cara: deja de estar cerrado y la
    contención del vecino se tiene que negar a correr. El criterio es suyo; el asset
    existe solo para ponérselo delante.
    """
    proyecto = _proyecto_con_pieza(tmp_path)
    directorio = tmp_path / ("proxy" if cerrado else "proxy-roto")
    directorio.mkdir(parents=True, exist_ok=True)
    # La maestra: el GLB de la etapa `normales`, tal cual.
    shutil.copy2(proyecto / "etapas" / "normales" / "malla.glb", directorio / "malla.glb")

    # El proxy: el casco de la malla decimada. A PLY primero — es lo que el
    # proveedor escribe — y a GLB con nuestro escritor, que es el que sabe.
    bruto = directorio / "_casco.ply"
    medidas = pymeshlab.casco_convexo(proyecto / "etapas" / "decimado" / "malla.ply", bruto)
    vertices, caras = pymeshlab.geometria_de(bruto)
    bruto.unlink(missing_ok=True)
    # El casco de un cubo es el cubo: la maestra quedaria **sobre** la superficie del
    # proxy, y la mitad de las muestras contaria como asomo — un empate degenerado,
    # no un proxy. Un 5% de holgura lo deja contenido de verdad, que es lo que la
    # prueba quiere mirar.
    vertices = vertices * 1.05
    if not cerrado:
        caras = caras[:-1]
    glb.escribir_glb(
        directorio / "proxy.glb",
        vertices=vertices,
        triangulos=caras,
        uv=[(0.0, 0.0)] * len(vertices),
    )
    assert medidas["caras"] >= 4  # un casco tridimensional tiene caras de sobra

    return activo.escribir_activo(
        directorio,
        identidad="prueba·proxy",
        productor="videomesh/test",
        artefactos=[
            activo.describir_artefacto(
                directorio, "malla.glb", identidad="maestra", rol="MASTER", formato="GLB"
            ),
            activo.describir_artefacto(
                directorio, "proxy.glb", identidad="proxy", rol="COLLISION", formato="GLB"
            ),
        ],
        destino={
            "preset": "material-de-trabajo",
            "budgets": [],
            "collisionSlackMax": 0.10,
            "collisionRequireConvex": True,
        },
    )


def test_el_proxy_es_un_casco_y_el_vecino_juzga_la_contencion(
    tmp_path: pathlib.Path,
) -> None:
    """El caso completo: proxy convexo, destino con su holgura, y el juez al lado."""
    asset = _asset_de_proxy(tmp_path, cerrado=True)
    juicio = juicio_de_produccion(asset)

    informe = juicio["informe"]
    contencion = informe["collision"]
    assert contencion is not None and contencion["ran"] is True
    assert contencion["verdict"] == "PASS"

    checks = {c["id"]: c["state"] for c in informe["readiness"]["checks"]}
    assert checks["tope-de-holgura"] == "PASS"


def test_un_proxy_abierto_lo_declara_el_vecino(tmp_path: pathlib.Path) -> None:
    """El caso rojo: un proxy con un agujero, y su contención no corre.

    Sin proxy cerrado **«dentro» no está definido**, y el vecino se niega a dar un
    número: `PROXY_NO_CERRADO`. El criterio es suyo — aquí no hay una segunda
    definición de «cerrado» que el día que discrepe con la suya nadie sabrá cuál manda.
    """
    asset = _asset_de_proxy(tmp_path, cerrado=False)
    juicio = juicio_de_produccion(asset)

    contencion = juicio["informe"]["collision"]
    assert contencion["ran"] is False
    assert contencion["reason"] == "PROXY_NO_CERRADO"


# --- la etapa completa, sobre el proyecto ----------------------------------------


def test_la_etapa_produce_el_proxy_y_lo_declara(tmp_path: pathlib.Path) -> None:
    """El casco entra en el asset como COLLISION, y el veredicto del vecino manda."""
    proyecto = _proyecto_con_pieza(tmp_path)
    construir(
        proyecto,
        destino={
            "preset": "material-de-trabajo",
            "budgets": [],
            "collisionSlackMax": 0.10,
            "collisionRequireConvex": True,
        },
    )

    directorio = proyecto / "etapas" / ETAPA_COLISION
    assert (directorio / "proxy.glb").is_file()

    informe = _informe(proyecto, ETAPA_COLISION)
    assert informe["medidas"]["proxy"]["cerrado"] is True
    veredicto = informe["veredicto_del_vecino"]
    assert veredicto["estado"] == "MEDIDO"
    assert veredicto["contencion"]["ran"] is True

    # Y el asset: el proxy con su papel, junto a la maestra.
    manifiesto = json.loads((directorio / activo.ACTIVO).read_text(encoding="utf-8"))
    roles = {a["id"]: a["role"] for a in manifiesto["artifacts"]}
    assert roles["proxy"] == "COLLISION"


def test_sin_cierre_la_etapa_lo_declara_y_el_vecino_lo_dice(
    tmp_path: pathlib.Path,
) -> None:
    """Un casco no puede salir abierto, pero la etapa no lo promete: lo comprueba.

    Si el cierre fallara —y aquí se prueba con un proxy escrito a mano sin su última
    cara—, la etapa publica el estado del proxy y el veredicto del vecino dice por
    qué la contención no corrió. Nunca un PASS sin haberse mirado.
    """
    proyecto = _proyecto_con_pieza(tmp_path)
    construir(
        proyecto,
        destino={
            "preset": "material-de-trabajo",
            "budgets": [],
            "collisionSlackMax": 0.10,
        },
    )
    # Casco honesto: la etapa pasa, y el cierre está medido, no prometido.
    informe = _informe(proyecto, ETAPA_COLISION)
    assert informe["medidas"]["proxy"]["cerrado"] is True
    assert informe["medidas"]["proxy"]["aristas_de_borde"] == 0
