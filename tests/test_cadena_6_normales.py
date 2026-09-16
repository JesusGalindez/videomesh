"""Encargo 04, D2 — el mapa de normales, y el juez que dice si lo es.

El horneado del encargo tenia una decision abierta —hacerlo aqui o llamar al trazador
del vecino— y este bloque la resuelve en tres trozos, cada uno donde vive:

    la correspondencia   aqui, con un vecino mas cercano probado contra fuerza bruta
    la rasterizacion     en el proveedor de malla, que escribe los texeles del atlas
    la medida y el juicio en el vecino, que no se reimplementan

Lo que estas pruebas defienden, por orden de importancia:

- **El marco de la UV esta bien, y se comprueba, no se promete.** Un mapa escrito en un
  marco torcido se lee sin error y sale con el relieve girado: es un fallo que se ve en
  el resultado y no en el proceso. Se prueba con un cuadrado cuya UV se conoce, donde el
  marco se puede escribir a mano y comparar.
- **El vecino distingue un mapa de normales de lo que no lo es.** Su R13 rechaza un mapa
  en espacio de objeto —que es lo que el proveedor escribe si se le pide su propia
  normal— porque su azul cae bajo el horizonte en la mitad de los texeles. El atlas que
  produce la etapa pasa el mismo tope: si los dos pasaran, o los dos fallaran, esa
  prueba no distinguiria nada.
- **El angulo que se publica es el del fichero**, no el de la intencion: se mide contra
  el mapa releido, y su suelo es el del formato —ocho bits por canal—, que se publica
  junto a el para que un decimo de grado no parezca un error del horneado.
"""

import json
import math
import pathlib
from typing import Any

import numpy as np
import pytest

from videomesh.adapters import geometria, glb, pymeshlab
from videomesh.adapters.softsight import juicio_de_produccion
from videomesh.application.decimado import decimar
from videomesh.application.densa import importar_paquete
from videomesh.application.limpieza import limpiar
from videomesh.application.normales import (
    ETAPA,
    GLB,
    MAPA,
    angulo_entre,
    hornear,
    suelo_de_cuantizacion_grados,
)
from videomesh.application.uv import PRODUCCION, cortar_y_empaquetar
from videomesh.cli.app import main
from videomesh.domain.malla import Malla
from videomesh.formatos.obj import escribir_obj_coloreado
from videomesh.formatos.ply import escribir_ply_malla
from videomesh.project import activo
from videomesh.project.informe import leer_informe
from videomesh.project.sellado import publicar_paquete
from videomesh.project.store import crear_proyecto

JUEZ_AUSENTE = pathlib.Path("/no/existe/production.mjs")

#: Lo que R13 contesta cuando lo que hay en una textura de normales no es una normal en
#: espacio tangente. El texto es suyo y se lee de su fuente, no se copia de memoria.
NO_PARECE_DE_NORMALES = "CONTENIDO_NO_PARECE_UN_MAPA_DE_NORMALES"


# --- mallas de prueba ---------------------------------------------------------


def _plano_con_bulto(*, divisiones: int, altura: float, anchura: float = 0.02) -> Malla:
    """Una rejilla cuadrada con un bulto en el centro, o plana si la altura es cero.

    Es la malla que hace falta para que el mapa tenga algo que contar: la densa lleva el
    bulto y su decimada lo aplana, asi que el horneado tiene un relieve de verdad que
    devolver. Con un cubo liso el mapa saldria plano y la prueba no probaria nada.

    El bulto es suave **a proposito**, y no es estetica: un bulto alto y estrecho decimado
    a doscientos triangulos se pliega, y un pliegue deja vertices de la malla de trabajo
    con la normal del reves. Eso no es un fallo del horneado —es un agujero de la malla— y
    ensuciaria lo que la prueba quiere medir.
    """
    vertices: list[tuple[float, float, float]] = []
    for j in range(divisiones + 1):
        for i in range(divisiones + 1):
            x = i / divisiones - 0.5
            y = j / divisiones - 0.5
            radio = math.sqrt(x * x + y * y)
            z = altura * math.exp(-(radio * radio) / anchura) if altura > 0 else 0.0
            vertices.append((x, y, z))

    triangulos: list[tuple[int, int, int]] = []
    ancho = divisiones + 1
    for j in range(divisiones):
        for i in range(divisiones):
            a = j * ancho + i
            triangulos += [(a, a + 1, a + ancho + 1), (a, a + ancho + 1, a + ancho)]
    return Malla(vertices=vertices, triangulos=triangulos)


def _proyecto_con_bulto(tmp_path: pathlib.Path, *, objetivo: int = 200) -> pathlib.Path:
    """Un proyecto con la cadena hasta el atlas: la entrada de esta etapa."""
    proyecto = tmp_path / "proyecto"
    crear_proyecto(proyecto, nombre="prueba")
    paquete = tmp_path / "densa-0001"
    with publicar_paquete(paquete, package_id="densa-0001", producer="producers/colmap") as obra:
        escribir_ply_malla(
            obra.raiz / "malla.ply", _plano_con_bulto(divisiones=48, altura=0.06, anchura=0.12)
        )
        obra.anadir("malla.ply", identidad="malla", tipo="TRIANGLE_MESH", purely_reconstructed=True)
        obra.manifest["requiredEvidence"] = ["malla"]
    importar_paquete(proyecto, paquete, maquina="colab-t4")
    limpiar(proyecto)
    decimar(proyecto, objetivo=objetivo)
    cortar_y_empaquetar(proyecto)
    return proyecto


def _informe(proyecto: pathlib.Path) -> dict[str, Any]:
    documento = leer_informe(proyecto, ETAPA)
    assert documento is not None
    return documento


def _situacion(proyecto: pathlib.Path, etapa: str) -> str:
    from videomesh.application.cadena import estado_de_la_cadena

    return str(next(p for p in estado_de_la_cadena(proyecto) if p.etapa == etapa).situacion.value)


# --- la geometria, sin malla y sin proveedor ----------------------------------


def test_el_marco_de_la_uv_sale_de_la_derivada_de_la_posicion() -> None:
    """Un cuadrado en el plano XY con la UV alineada: el marco se sabe a mano.

    Si esto estuviera mal, el mapa saldria con el relieve girado y nada lo diria. La
    tangente es `dP/du` y la bitangente `dP/dv`, asi que aqui tienen que ser +X y +Y.
    """
    vertices = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]], dtype="float64"
    )
    caras = np.array([[0, 1, 2], [0, 2, 3]], dtype="int64")
    uv = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]], dtype="float64")

    marcos = geometria.marcos_de_uv(vertices, caras, uv)
    assert np.allclose(marcos["tangente"], np.tile([1.0, 0.0, 0.0], (4, 1)), atol=1e-9)
    assert np.allclose(marcos["bitangente"], np.tile([0.0, 1.0, 0.0], (4, 1)), atol=1e-9)
    assert np.allclose(marcos["normal"], np.tile([0.0, 0.0, 1.0], (4, 1)), atol=1e-9)
    assert marcos["triangulos_reflejados"] == 0
    assert geometria.es_marco(marcos)


def test_una_uv_reflejada_se_cuenta_y_el_marco_sigue_siendo_ortonormal() -> None:
    """La trampa del horneado, con su numero.

    Con la UV espejada, `dP/du` apunta al contrario que `N x T`. El triangulo se cuenta
    —es lo que un visor tiene que derivar con el bit de handedness de la especificacion—y
    el marco se queda ortonormal igual.
    """
    vertices = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]], dtype="float64"
    )
    caras = np.array([[0, 1, 2], [0, 2, 3]], dtype="int64")
    uv = np.array([[1.0, 0.0], [0.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype="float64")

    marcos = geometria.marcos_de_uv(vertices, caras, uv)
    assert marcos["triangulos_reflejados"] == 2
    assert geometria.es_marco(marcos)


def test_un_marco_torcido_no_pasa_la_comprobacion() -> None:
    """El caso rojo de la comprobacion, sin malla: dos ejes que no son perpendiculares."""
    bueno = {
        "tangente": np.tile([1.0, 0.0, 0.0], (3, 1)),
        "bitangente": np.tile([0.0, 1.0, 0.0], (3, 1)),
        "normal": np.tile([0.0, 0.0, 1.0], (3, 1)),
    }
    assert geometria.es_marco(bueno)

    torcido = dict(bueno)
    torcido["bitangente"] = np.tile([0.5, 0.5, 0.0], (3, 1))
    assert not geometria.es_marco(torcido)

    corto = dict(bueno)
    corto["normal"] = np.tile([0.0, 0.0, 0.5], (3, 1))
    assert not geometria.es_marco(corto)


def test_la_normal_de_un_cubo_es_la_de_su_cara() -> None:
    """La normal suave, ponderada por area, con un resultado que se sabe a mano."""
    malla = _plano_con_bulto(divisiones=1, altura=0.0)
    vertices = np.array(malla.vertices, dtype="float64")
    caras = np.array(malla.triangulos, dtype="int64")
    normales = geometria.normales_de_vertice(vertices, caras)
    assert np.allclose(normales, np.tile([0.0, 0.0, 1.0], (len(vertices), 1)), atol=1e-9)


def test_el_vecino_mas_cercano_es_el_de_la_fuerza_bruta() -> None:
    """La rejilla acelera una consulta; no cambia su respuesta.

    Se comprueba contra recorrer los puntos uno a uno, que es la unica forma de saber que
    el indice es correcto. La nube esta descentrada a proposito: una rejilla que se crea
    centrada en el origen consulta celdas que no son.
    """
    generador = np.random.default_rng(20260916)
    nube = generador.normal(loc=(7.0, -3.0, 2.0), scale=0.4, size=(600, 3))
    consultas = generador.normal(loc=(7.0, -3.0, 2.0), scale=0.6, size=(120, 3))

    vecindad = geometria.Vecindad(nube)
    distancias = vecindad.mas_cercano(consultas).distancias

    bruto = np.sqrt(((consultas[:, None, :] - nube[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
    assert np.allclose(distancias, bruto, atol=1e-9)


def test_la_correspondencia_orientada_no_cruza_una_pared_delgada() -> None:
    """El fallo que aparecio sobre la malla real, reducido a dos hojas paralelas.

    Dos planos a distancia de cuatro milésimas: el de arriba, grueso —un vertice cada
    cuatro centésimas— y el de abajo, fino. Una consulta justo por encima del de arriba
    esta **mas cerca** de un vertice del de abajo que del suyo, y con el vecino a secas se
    lleva la normal de abajo, que mira al reves. Con la orientacion se lleva la de arriba,
    que es la que corresponde. Medido sobre la malla de Colab: 2,4 % de los texeles
    mirando hacia dentro, y R13 lo rechaza.
    """
    arriba = np.array([(x, y, 0.0) for x in (0.0, 0.04) for y in (0.0, 0.04)], dtype="float64")
    abajo = np.array(
        [(x, y, -0.004) for x in np.arange(0.0, 0.05, 0.005) for y in (0.0,)], dtype="float64"
    )
    arriba_n = np.tile([0.0, 0.0, 1.0], (len(arriba), 1))
    abajo_n = np.tile([0.0, 0.0, -1.0], (len(abajo), 1))
    nube = np.vstack([arriba, abajo])
    normales = np.vstack([arriba_n, abajo_n])

    consulta = np.array([[0.0, 0.0, -0.0030]], dtype="float64")
    referencia = np.array([[0.0, 0.0, 1.0]], dtype="float64")
    vecindad = geometria.Vecindad(nube, normales)

    a_secas = vecindad.mas_cercano(consulta)
    assert float(a_secas.distancias[0]) == pytest.approx(0.001)
    assert float(normales[a_secas.indices[0]][2]) < 0.0, "por cercania se lleva la de abajo"

    orientada = vecindad.mas_cercano(consulta, referencia=referencia)
    assert float(normales[orientada.indices[0]][2]) > 0.0, (
        "con la orientacion tiene que llevarse la de arriba, que mira al mismo lado"
    )
    assert orientada.sin_orientacion == 0


def test_sin_ningun_vecino_orientado_se_cuenta_y_se_sigue() -> None:
    """Una consulta que no encuentra a nadie mirando hacia su lado no para la etapa."""
    nube = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype="float64")
    normales = np.tile([0.0, 0.0, -1.0], (2, 1))
    consulta = np.array([[0.4, 0.0, 0.0]], dtype="float64")

    vecindad = geometria.Vecindad(nube, normales)
    orientada = vecindad.mas_cercano(consulta, referencia=np.array([[0.0, 0.0, 1.0]]))
    assert orientada.sin_orientacion == 1
    assert int(orientada.indices[0]) in (0, 1)
    assert float(orientada.distancias[0]) == pytest.approx(0.4)


def test_el_paso_de_la_malla_se_mide_y_no_se_supone() -> None:
    """Sobre una rejilla regular el paso se sabe; el numero tiene que salir de la medida."""
    rejilla = np.array([(x, y, 0.0) for x in range(10) for y in range(10)], dtype="float64")
    paso = geometria.medir_paso_de_la_malla(rejilla)
    assert paso["mediano"] == pytest.approx(1.0, rel=1e-9)
    assert paso["p90"] == pytest.approx(1.0, rel=1e-9)


def test_el_angulo_entre_lo_pedido_y_lo_que_quedo_es_el_que_es() -> None:
    """El numero de cierre de la etapa, probado con vectores inventados: 10 grados son 10.

    Se recibe por argumento y no se lee de ningun fichero, asi que su caso rojo existe sin
    hornear nada: un vector girado un cuarto de vuelta tiene que salir 90.
    """
    pedido = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]])
    diez = math.radians(10.0)
    leido = np.array([[0.0, math.sin(diez), math.cos(diez)], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0]])
    angulos = angulo_entre(pedido, leido)
    assert angulos[0] == pytest.approx(10.0, abs=1e-6)
    assert angulos[1] == pytest.approx(0.0, abs=1e-6)
    assert angulos[2] == pytest.approx(90.0, abs=1e-6)


def test_el_suelo_de_cuantizacion_es_el_del_formato() -> None:
    """Ocho bits por canal: medio paso de cuantia es el fondo del que se puede bajar."""
    assert suelo_de_cuantizacion_grados() == pytest.approx(math.degrees((0.5 / 255) * math.sqrt(3)))


# --- la etapa, con malla de verdad --------------------------------------------


def test_la_etapa_publica_el_mapa_y_lo_declara_con_su_papel(tmp_path: pathlib.Path) -> None:
    """El mapa tiene que estar en el manifiesto con `usage: NORMAL`.

    Sin ese papel, R13 no lo audita —la textura se mira por lo que dice ser— y la etapa
    se quedaria sin juez, que es exactamente lo que el bloque viene a cerrar.
    """
    proyecto = _proyecto_con_bulto(tmp_path)
    hornear(proyecto, resolucion=512)

    directorio = proyecto / "etapas" / ETAPA
    assert (directorio / MAPA).is_file()
    assert (directorio / GLB).is_file()

    manifiesto = json.loads((directorio / activo.ACTIVO).read_text(encoding="utf-8"))
    textura = next(a for a in manifiesto["artifacts"] if a["role"] == "TEXTURE")
    assert textura["usage"] == "NORMAL"
    assert textura["path"] == MAPA
    # El mapa no es de un formato de malla: `format` es para PLY y GLB, y declararlo aqui
    # seria decir que el PNG es una malla.
    assert "format" not in textura
    # Y el destino declara lo que esta etapa promete cumplir: el lado de su mapa.
    assert manifiesto["target"]["textureMaxSize"] == 512
    assert manifiesto["target"]["texturePowerOfTwo"] is True


def _json_del_glb(ruta: pathlib.Path) -> dict[str, Any]:
    """El bloque JSON de un GLB, para poder mirar que atributos lleva la pieza."""
    datos = ruta.read_bytes()
    largo = int.from_bytes(datos[12:16], "little")
    documento: dict[str, Any] = json.loads(datos[20 : 20 + largo].decode("utf-8"))
    return documento


def test_la_pieza_sale_con_su_normal_escrita(tmp_path: pathlib.Path) -> None:
    """Un mapa de normales se lee **contra la normal de la malla**.

    Si la pieza no la trae, el visor se la inventa y el relieve sale desplazado sin que
    nada lo diga. Y tiene que ser la misma con la que se construyo el marco: la del
    vertice, ponderada por area, no la de la cara.
    """
    proyecto = _proyecto_con_bulto(tmp_path)
    hornear(proyecto, resolucion=256)

    documento = _json_del_glb(proyecto / "etapas" / ETAPA / GLB)
    atributos = documento["meshes"][0]["primitives"][0]["attributes"]
    assert "NORMAL" in atributos
    acceso = documento["accessors"][atributos["NORMAL"]]
    assert acceso["type"] == "VEC3"

    atlas = pymeshlab.leer_atlas(proyecto / "etapas" / ETAPA / GLB)
    normales = geometria.normales_de_vertice(atlas.vertices, atlas.caras)
    assert acceso["count"] == len(normales)
    assert np.allclose(np.linalg.norm(normales, axis=1), 1.0, atol=1e-6)
    # La superficie de prueba esta casi plana y mira a +Z: si lo que se escribio fuera
    # otra cosa —la normal de la cara, un cero— la direccion lo delataria.
    assert float(np.mean(normales[:, 2])) > 0.9


def test_el_mapa_que_produce_la_etapa_pasa_la_auditoria_del_vecino(tmp_path: pathlib.Path) -> None:
    """Y sus tres numeros son suyos: azul medio, longitud y texeles bajo el horizonte."""
    proyecto = _proyecto_con_bulto(tmp_path)
    hornear(proyecto, resolucion=512)

    veredicto: dict[str, Any] = _informe(proyecto)["veredicto_del_vecino"]
    assert veredicto["estado"] == "MEDIDO"
    assert veredicto["certificacion"] == "PASS"
    normal = veredicto["normal"]
    assert normal["usage"] == "NORMAL"
    assert normal["width"] == 512 and normal["height"] == 512
    assert normal["powerOfTwo"] is True
    assert "reason" not in normal
    # La z de un mapa de normales en espacio tangente no apunta hacia dentro: por debajo
    # del horizonte no hay casi nada. Un mapa en espacio de objeto tendria la mitad.
    assert normal["normalLike"]["belowHorizonRatio"] <= 0.001
    assert normal["normalLike"]["meanBlue"] >= 0.5


def _esfera(*, meridianos: int = 48, paralelos: int = 24) -> tuple[Any, Any, Any]:
    """Una esfera con UV de latitud y longitud: una superficie donde la normal apunta a
    todas partes, que es lo que hace falta para que el espacio de objeto y el tangente no
    coincidan. En un plano casi liso los dos son el mismo y no se distinguiria nada.
    """
    vertices: list[tuple[float, float, float]] = []
    uv: list[tuple[float, float]] = []
    for j in range(paralelos + 1):
        latitud = math.pi * (j / paralelos - 0.5)
        for i in range(meridianos + 1):
            longitud = 2.0 * math.pi * (i / meridianos)
            vertices.append(
                (
                    math.cos(latitud) * math.cos(longitud),
                    math.cos(latitud) * math.sin(longitud),
                    math.sin(latitud),
                )
            )
            uv.append((i / meridianos, j / paralelos))

    triangulos: list[tuple[int, int, int]] = []
    ancho = meridianos + 1
    for j in range(paralelos):
        for i in range(meridianos):
            a = j * ancho + i
            triangulos += [(a, a + 1, a + ancho + 1), (a, a + ancho + 1, a + ancho)]
    return (
        np.array(vertices, dtype="float64"),
        np.array(triangulos, dtype="int64"),
        np.array(uv, dtype="float64"),
    )


def test_un_mapa_en_espacio_de_objeto_lo_rechaza_su_auditoria(tmp_path: pathlib.Path) -> None:
    """El caso rojo, y es el que decide si la etapa esta hecha.

    Un mapa en espacio de objeto es lo que el proveedor escribe si se le pide **su**
    normal, y R13 lo distingue: su azul cae bajo el horizonte en la mitad de los texeles,
    porque la mitad de una esfera mira hacia dentro en el eje Z del objeto. El rechazo
    tiene que venir de su auditoria y no de una comprobacion de aqui.
    """
    directorio = tmp_path / "asset"
    directorio.mkdir(parents=True)
    vertices, caras, uv = _esfera()
    objetos: Any = vertices / np.linalg.norm(vertices, axis=1)[:, None]
    glb.escribir_glb(directorio / GLB, vertices=vertices, triangulos=caras, uv=uv)

    coloreado = directorio / "_objeto.obj"
    escribir_obj_coloreado(
        coloreado,
        vertices=vertices,
        caras=caras,
        uv=uv,
        colores=np.clip((objetos + 1.0) / 2.0, 0.0, 1.0),
    )
    malo = directorio / "_objeto.png"
    try:
        pymeshlab.hornear_colores(coloreado, malo, resolucion=256, pullpush=True)
        asset = activo.escribir_activo(
            directorio,
            identidad="prueba·objeto",
            productor="videomesh/normales",
            artefactos=[
                activo.describir_artefacto(
                    directorio, GLB, identidad="maestra", rol="MASTER", formato="GLB"
                ),
                activo.describir_artefacto(
                    directorio, malo.name, identidad=malo.name, rol="TEXTURE", usage="NORMAL"
                ),
            ],
            destino={"preset": "prueba", "budgets": []},
        )
        juicio = juicio_de_produccion(asset)
    finally:
        coloreado.unlink(missing_ok=True)
        malo.unlink(missing_ok=True)

    assert juicio["certificacion"] == "FAIL"
    assert juicio["motivo"] == NO_PARECE_DE_NORMALES
    textura = next(t for t in juicio["informe"]["textures"] if t["usage"] == "NORMAL")
    assert textura["normalLike"]["belowHorizonRatio"] > 0.3, (
        "la mitad de un mapa en espacio de objeto mira hacia dentro de la superficie, y "
        f"el vecino mide {textura['normalLike']['belowHorizonRatio']}"
    )


def test_el_angulo_publicado_es_el_del_fichero_y_no_el_de_la_intencion(
    tmp_path: pathlib.Path,
) -> None:
    """Lo que cuesta el viaje: rasterizar, interpolar y redondear a ocho bits.

    Se mide contra el mapa **releido**, asi que incluye el redondeo del formato; por eso
    el suelo de cuantizacion se publica al lado. Un mapa con el relieve girado daria
    decenas de grados, y el de la etapa tiene que quedar muy por debajo.
    """
    proyecto = _proyecto_con_bulto(tmp_path)
    hornear(proyecto, resolucion=512)

    medidas: dict[str, Any] = _informe(proyecto)["medidas"]
    angulo = medidas["angulo"]
    assert angulo["suelo_de_cuantizacion"] == pytest.approx(suelo_de_cuantizacion_grados())
    assert angulo["medio"] < 2.0, f"el angulo medio es {angulo['medio']} grados"
    assert angulo["maximo"] < 15.0, f"el angulo maximo es {angulo['maximo']} grados"
    # Y no es el suelo del formato: hay algo mas que redondeo, que es el relieve.
    assert angulo["medio"] >= angulo["suelo_de_cuantizacion"] / 2.0


def test_la_etapa_publica_la_aproximacion_y_la_resolucion(tmp_path: pathlib.Path) -> None:
    """El vecino es un vertice y no el punto de una cara: hay que poder juzgarlo.

    Se publican el paso de la malla medida y la distancia a ese vertice, y la distancia
    tiene que ser del orden del paso: si fuera mucho mayor, la malla medida y la de
    trabajo no serian la misma superficie.
    """
    proyecto = _proyecto_con_bulto(tmp_path)
    hornear(proyecto, resolucion=256)

    medidas: dict[str, Any] = _informe(proyecto)["medidas"]
    paso = medidas["paso_de_la_malla_medida"]
    vecino = medidas["vecino_mas_cercano"]
    assert paso["mediano"] > 0
    assert paso["muestras"] > 0
    assert vecino["mediana"] <= paso["mediano"]
    assert vecino["maxima"] <= paso["mediano"] * 3.0
    assert medidas["resolucion"] == {"lado": 256, "texeles": 256 * 256}


def test_el_mapa_es_determinista(tmp_path: pathlib.Path) -> None:
    """Lo que justifica declarar la etapa `DETERMINISTA` y poder saltarsela."""
    primero = _proyecto_con_bulto(tmp_path / "uno")
    segundo = _proyecto_con_bulto(tmp_path / "dos")
    hornear(primero, resolucion=256)
    hornear(segundo, resolucion=256)

    salidas = [s for s in _informe(primero)["salidas"] if s["id"] == MAPA]
    otras = [s for s in _informe(segundo)["salidas"] if s["id"] == MAPA]
    assert salidas[0]["sha256"] == otras[0]["sha256"]


def test_el_mapa_caduca_cuando_cambia_el_atlas(tmp_path: pathlib.Path) -> None:
    """§9 con su caso concreto, y el que justifica que el atlas entre en el hash.

    Un mapa se escribe en el espacio de una UV. Si se corta el atlas otra vez —mismo
    decimado, otro corte— el mapa describe una superficie que ya no es la suya, y eso hay
    que verlo en `status` sin lanzar nada.
    """
    proyecto = _proyecto_con_bulto(tmp_path)
    hornear(proyecto, resolucion=256)
    assert _situacion(proyecto, ETAPA) == "HECHA"

    # Otro corte del mismo decimado: el margen entra en los parametros de la etapa de UV,
    # asi que su hash de salida cambia.
    cortar_y_empaquetar(proyecto, margen=6)
    assert _situacion(proyecto, ETAPA) == "CADUCADA"


def test_sin_el_juez_la_etapa_produce_y_declara_que_no_se_pudo_juzgar(
    tmp_path: pathlib.Path,
) -> None:
    """Un verde por omision seria la peor salida posible: se publica `NOT_RUN`."""
    proyecto = _proyecto_con_bulto(tmp_path)
    hornear(proyecto, resolucion=256, herramienta_de_produccion=JUEZ_AUSENTE)

    directorio = proyecto / "etapas" / ETAPA
    assert (directorio / MAPA).is_file(), "el mapa se produce igual: lo que falta es el juez"

    informe = _informe(proyecto)
    veredicto: dict[str, Any] = informe["veredicto_del_vecino"]
    assert veredicto["estado"] == "NOT_RUN"
    assert "production.mjs" in str(veredicto["motivo"])
    assert any(p["que"] == "veredicto_de_produccion" for p in informe["no_comprobado"])
    assert not (directorio / PRODUCCION).exists()


def test_con_lo_producido_borrado_no_se_devuelve_lo_que_no_esta(
    tmp_path: pathlib.Path,
) -> None:
    """El registro dice si la entrada cambió; no dice si lo que produjo sigue en su sitio.

    Un mapa borrado con el registro intacto daba un «ya está hecho» que devolvía el
    informe de una etapa cuyo PNG no estaba —y el mapa es justo lo que la etapa de
    material va a leer—. Lo que hay en disco se comprueba antes de creerse el registro.
    """
    proyecto = _proyecto_con_bulto(tmp_path)
    hornear(proyecto, resolucion=256)
    assert _situacion(proyecto, ETAPA) == "HECHA"

    (proyecto / "etapas" / ETAPA / MAPA).unlink()
    informe = hornear(proyecto, resolucion=256)
    assert informe.is_file()
    assert (informe.parent / MAPA).is_file(), "el mapa se rehace, no se cita de memoria"


def test_la_orden_ensena_el_angulo_y_el_juicio_del_vecino(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """La salida de `videomesh normales`: el numero que costo, y quien lo juzgo."""
    proyecto = _proyecto_con_bulto(tmp_path)
    assert main(["normales", str(proyecto), "--resolucion", "256"]) == 0
    salida = capsys.readouterr().out
    assert "angulo contra lo pedido" in salida
    assert "suelo del formato" in salida
    assert "informe del vecino          PASS" in salida
    assert "paso de la medida" in salida
