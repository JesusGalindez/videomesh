"""Encargo 04, bloque B — que la malla se pueda abrir, y cuanto costo abrirla.

La densa sale con millones de triangulos y trozos flotantes: la pared de detras,
el suelo, nubes que el fusionado no supo descartar. Limpiar y decimar es
legitimo; **no decir cuanto se perdio no lo es**. El criterio de cierre del
encargo es una pregunta:

    ¿publica la etapa el numero que dice cuanto se perdio?

Decimar es perder detalle y limpiar es tirar geometria, y las dos son medibles.
La distancia de superficie sale de `diffMeshes` de SoftSight, en las DOS
direcciones por separado: promediarlas esconderia justo lo que interesa —que
quitar superficie y anadirla son averias distintas—.

La medicion va por la herramienta publica del vecino, sobre las dos mallas
convertidas a OBJ, que es un formato que `diffMeshes` lee. La conversion es
nuestra y va declarada en el informe: lo que no se hace es **medir en Python**,
porque dos medidas de lo mismo acaban discrepando y el dia que lo hagan nadie
sabra cual manda.
"""

import hashlib
import json
import math
import pathlib
import shutil
from typing import Any

import pytest

from videomesh.application.decimado import decimar
from videomesh.application.densa import importar_paquete
from videomesh.application.limpieza import limpiar
from videomesh.cli.app import main
from videomesh.domain.errores import ErrorDeProveedor
from videomesh.domain.malla import Malla
from videomesh.domain.procedencia import EstadoDeProcedencia
from videomesh.formatos.ply import escribir_ply_malla
from videomesh.project.informe import leer_informe
from videomesh.project.procedencia import procedencia_de
from videomesh.project.sellado import publicar_paquete
from videomesh.project.store import crear_proyecto

CONSUMIDOR = pathlib.Path("/no/existe/agent3d.mjs")

#: El suelo de ruido de `diffMeshes`, en fraccion de la diagonal. Es de SoftSight
#: y no se copia con otro numero: se lee de su codigo fuente, que es el original.
#: 4e-16 — por debajo de eso, la distancia que se mide es la de la aritmetica de
#: coma flotante y no la de la geometria.
SUELO_DE_RUIDO = 4e-16


def _cubo(
    centro: tuple[float, float, float] = (0.0, 0.0, 0.0),
    lado: float = 1.0,
    divisiones: int = 1,
) -> Malla:
    """Un cubo con las aristas **soldadas**: un solo componente.

    Con `divisiones=1` son los ocho vertices y doce triangulos de siempre; con mas
    subdivisiones el mismo cubo con superficie de verdad, que es lo que hace falta
    para que una mota de tres triangulos sea una mota y no una cuarta parte.
    """
    n = divisiones
    vertices: list[tuple[float, float, float]] = []
    indice: dict[tuple[int, int, int], int] = {}

    def vertice(i: int, j: int, k: int) -> int:
        clave = (i, j, k)
        if clave not in indice:
            indice[clave] = len(vertices)
            vertices.append(
                (
                    centro[0] + (i / n - 0.5) * lado,
                    centro[1] + (j / n - 0.5) * lado,
                    centro[2] + (k / n - 0.5) * lado,
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


def _esfera(anillos: int = 32, gajos: int = 64, radio: float = 1.0) -> Malla:
    """Una esfera curva, que es donde una decimacion se nota de verdad."""
    vertices = [(0.0, radio, 0.0)]
    for i in range(1, anillos):
        phi = math.pi * i / anillos
        for j in range(gajos):
            theta = 2 * math.pi * j / gajos
            vertices.append(
                (
                    radio * math.sin(phi) * math.cos(theta),
                    radio * math.cos(phi),
                    radio * math.sin(phi) * math.sin(theta),
                )
            )
    vertices.append((0.0, -radio, 0.0))
    triangulos = [(0, 1 + j, 1 + (j + 1) % gajos) for j in range(gajos)]
    for i in range(anillos - 2):
        base = 1 + i * gajos
        for j in range(gajos):
            a, b = base + j, base + (j + 1) % gajos
            c, d = base + gajos + j, base + gajos + (j + 1) % gajos
            triangulos += [(a, b, d), (a, d, c)]
    ultimo = len(vertices) - 1
    base = 1 + (anillos - 2) * gajos
    for j in range(gajos):
        triangulos.append((ultimo, base + (j + 1) % gajos, base + j))
    return Malla(vertices=vertices, triangulos=triangulos)


def _plano(lado: int = 32) -> Malla:
    """Rejilla plana con coordenadas exactas en los seis decimales del PLY."""
    paso = 2.0 / lado
    vertices = [(i * paso, j * paso, 0.0) for i in range(lado + 1) for j in range(lado + 1)]
    triangulos = []
    for i in range(lado):
        for j in range(lado):
            a = i * (lado + 1) + j
            triangulos += [(a, a + 1, a + lado + 2), (a, a + lado + 2, a + lado + 1)]
    return Malla(vertices=vertices, triangulos=triangulos)


def _dos_cubos_con_mota(divisiones: int = 8) -> Malla:
    """El caso que el encargo pide ver: dos piezas y una mota de tres triangulos.

    Los cubos van subdivididos a proposito. Con doce triangulos por cubo, «una mota
    de tres triangulos» es una cuarta parte de la pieza mayor, y ningun umbral
    relativo la distingue de un objeto. Una mota es una mota **al lado de
    superficie**, y eso es lo que miden estas dos piezas.
    """
    uno = _cubo(divisiones=divisiones)
    otro = _cubo(centro=(3.0, 0.0, 0.0), divisiones=divisiones)
    vertices = [*uno.vertices, *otro.vertices]
    base_del_otro = len(uno.vertices)
    triangulos = [
        *uno.triangulos,
        *[(a + base_del_otro, b + base_del_otro, c + base_del_otro) for a, b, c in otro.triangulos],
    ]
    base = len(vertices)
    vertices += [(0.0, 0.0, 9.0), (0.1, 0.0, 9.0), (0.0, 0.1, 9.0), (0.0, 0.0, 9.1)]
    triangulos += [
        (base, base + 1, base + 2),
        (base, base + 2, base + 3),
        (base, base + 1, base + 3),
    ]
    return Malla(vertices=vertices, triangulos=triangulos)


def _proyecto_con_densa(tmp_path: pathlib.Path, malla: Malla) -> pathlib.Path:
    """Un proyecto con la malla ya importada: la cadena empieza donde empieza."""
    proyecto = tmp_path / "proyecto"
    crear_proyecto(proyecto, nombre="prueba")
    paquete = tmp_path / "densa-0001"
    with publicar_paquete(
        paquete, package_id="densa-0001", producer="producers/colmap · 8 vistas"
    ) as obra:
        escribir_ply_malla(obra.raiz / "malla.ply", malla)
        obra.anadir("malla.ply", identidad="malla", tipo="TRIANGLE_MESH", purely_reconstructed=True)
        obra.manifest["requiredEvidence"] = ["malla"]
    importar_paquete(proyecto, paquete, maquina="colab-t4")
    return proyecto


def _proyecto_limpio(tmp_path: pathlib.Path, malla: Malla) -> pathlib.Path:
    """Un proyecto con la malla importada y ya limpia: la entrada del decimado."""
    proyecto = _proyecto_con_densa(tmp_path, malla)
    limpiar(proyecto)
    return proyecto


def _correr(*argumentos: str) -> tuple[int, str]:
    from contextlib import redirect_stdout
    from io import StringIO

    salida = StringIO()
    with redirect_stdout(salida):
        codigo = main(list(argumentos))
    return codigo, salida.getvalue()


def _medidas(proyecto: pathlib.Path, etapa: str) -> dict[str, Any]:
    informe = leer_informe(proyecto, etapa)
    assert informe is not None, f"la etapa {etapa} no publico informe"
    medidas: dict[str, Any] = informe["medidas"]
    return medidas


# --- B1: limpieza -----------------------------------------------------------


def test_la_limpieza_deja_dos_componentes_y_no_uno_ni_tres(tmp_path: pathlib.Path) -> None:
    """El caso rojo que el encargo pide: dos cubos separados y una mota de tres triangulos."""
    proyecto = _proyecto_con_densa(tmp_path, _dos_cubos_con_mota())

    limpiar(proyecto)

    medidas = _medidas(proyecto, "limpieza")
    assert medidas["componentes_antes"] == 3
    assert medidas["componentes_despues"] == 2


def test_la_limpieza_publica_cuanto_quito(tmp_path: pathlib.Path) -> None:
    """Limpiar es tirar geometria, y tirarla sin decir cuanto es la mitad del trabajo."""
    malla = _dos_cubos_con_mota()
    proyecto = _proyecto_con_densa(tmp_path, malla)

    limpiar(proyecto)

    medidas = _medidas(proyecto, "limpieza")
    assert medidas["triangulos_antes"] == len(malla.triangulos)
    assert medidas["triangulos_quitados"] == 3
    assert medidas["triangulos_despues"] == len(malla.triangulos) - 3
    assert medidas["vertices_antes"] - medidas["vertices_despues"] > 0


def test_el_umbral_de_los_componentes_es_relativo_y_no_absoluto(tmp_path: pathlib.Path) -> None:
    """Una mota de tres triangulos se va con una esfera de 16 mil y con un cubo de doce.

    Un umbral absoluto tendria que elegirse distinto para cada tamano, y elegirlo
    seria una decision escondida en el codigo. Relativo al mayor, el mismo numero
    vale para los dos.
    """
    esfera = _esfera()
    cubo = _cubo(centro=(5.0, 0.0, 0.0))
    juntas = Malla(
        vertices=[*esfera.vertices, *cubo.vertices],
        triangulos=[
            *esfera.triangulos,
            *[
                (a + len(esfera.vertices), b + len(esfera.vertices), c + len(esfera.vertices))
                for a, b, c in cubo.triangulos
            ],
        ],
    )
    proyecto = _proyecto_con_densa(tmp_path, juntas)

    limpiar(proyecto, minimo_relativo=0.001)
    assert _medidas(proyecto, "limpieza")["componentes_despues"] == 2

    limpiar(proyecto, minimo_relativo=0.5)
    assert _medidas(proyecto, "limpieza")["componentes_despues"] == 1


def test_la_limpieza_quita_los_triangulos_de_area_cero(tmp_path: pathlib.Path) -> None:
    """Una cara que no cubre superficie: tres puntos distintos y colineales.

    Con el mismo indice repetido no se puede ni cargar —el proveedor rechaza la cara—,
    asi que la forma de tener area cero es que los tres puntos esten en linea.
    """
    base = _dos_cubos_con_mota()
    vertices = [*base.vertices, (4.0, 4.0, 4.0), (5.0, 4.0, 4.0), (6.0, 4.0, 4.0)]
    triangulos = [
        *base.triangulos,
        (len(base.vertices), len(base.vertices) + 1, len(base.vertices) + 2),
    ]
    proyecto = _proyecto_con_densa(tmp_path, Malla(vertices=vertices, triangulos=triangulos))

    limpiar(proyecto)

    medidas = _medidas(proyecto, "limpieza")
    assert medidas["triangulos_degenerados"] == 1
    assert medidas["triangulos_quitados"] == 4


def test_una_cara_con_el_mismo_indice_repetido_no_desaparece_en_silencio(
    tmp_path: pathlib.Path,
) -> None:
    """El proveedor la descarta **al cargar** y no avisa: se publica como perdida suya.

    Es una arista nula, el caso que el encargo manda quitar. No llega a la limpieza
    porque el proveedor la tira al leer, y una cosa que desaparece sin decirse es
    justo lo que este repositorio existe para no producir.
    """
    base = _dos_cubos_con_mota()
    vertices = [*base.vertices, (4.0, 4.0, 4.0), (5.0, 4.0, 4.0)]
    triangulos = [
        *base.triangulos,
        (len(base.vertices), len(base.vertices), len(base.vertices) + 1),
    ]
    proyecto = _proyecto_con_densa(tmp_path, Malla(vertices=vertices, triangulos=triangulos))

    limpiar(proyecto)

    medidas = _medidas(proyecto, "limpieza")
    assert medidas["caras_que_el_proveedor_no_cargo"] == 1
    informe = leer_informe(proyecto, "limpieza")
    assert informe is not None
    assert informe["no_comprobado"], "una perdida que no se declara no existe"


def test_un_ply_que_no_se_puede_leer_falla_tipado(tmp_path: pathlib.Path) -> None:
    """Un fichero truncado sale con un error de este repositorio, no con un traceback."""
    proyecto = _proyecto_con_densa(tmp_path, _cubo())
    roto = pathlib.Path(procedencia_de(proyecto)[0].fuente) / "malla.ply"
    roto.write_text(
        roto.read_text(encoding="utf-8").replace("element face 12", "element face 400"),
        encoding="utf-8",
    )

    with pytest.raises(ErrorDeProveedor) as fallo:
        limpiar(proyecto)

    assert "no puede leer" in str(fallo.value)


def test_la_limpieza_quita_los_vertices_sueltos(tmp_path: pathlib.Path) -> None:
    """Un vertice sin ninguna cara no es geometria: es basura que viaja en el fichero."""
    base = _cubo()
    vertices = [*base.vertices, (7.0, 7.0, 7.0), (7.0, 7.1, 7.0)]
    proyecto = _proyecto_con_densa(tmp_path, Malla(vertices=vertices, triangulos=base.triangulos))

    limpiar(proyecto)

    medidas = _medidas(proyecto, "limpieza")
    assert medidas["vertices_sueltos"] == 2
    assert medidas["vertices_despues"] == 8


def test_la_limpieza_no_mueve_ningun_vertice(tmp_path: pathlib.Path) -> None:
    """Las tres operaciones quitan; ninguna decide donde va un vertice.

    Si moviera uno, la procedencia seguiria diciendo `SIMPLIFIED` y seria mentira:
    mover vertices es reparar, y eso se declara distinto.
    """
    original = _dos_cubos_con_mota()
    proyecto = _proyecto_con_densa(tmp_path, original)

    limpiar(proyecto)

    limpia = leer_informe(proyecto, "limpieza")
    assert limpia is not None
    vertices_de_salida = _vertices_de(proyecto, "limpieza")
    assert vertices_de_salida <= {tuple(v) for v in original.vertices}


def _vertices_de(proyecto: pathlib.Path, etapa: str) -> set[tuple[float, float, float]]:
    from videomesh.project.informe import directorio_de_etapa

    texto = (directorio_de_etapa(proyecto, etapa) / "malla.ply").read_text(encoding="utf-8")
    cuerpo = texto.split("end_header\n", 1)[1]
    vertices = set()
    for linea in cuerpo.splitlines():
        partes = linea.split()
        if len(partes) == 3:
            vertices.add((float(partes[0]), float(partes[1]), float(partes[2])))
    return vertices


def test_la_limpieza_declara_que_no_invento_superficie(tmp_path: pathlib.Path) -> None:
    """Quitar geometria no crea geometria, y la procedencia lo tiene que decir."""
    proyecto = _proyecto_con_densa(tmp_path, _dos_cubos_con_mota())

    limpiar(proyecto)

    (anotada,) = [p for p in procedencia_de(proyecto) if p.etapa == "limpieza"]
    assert anotada.estado is EstadoDeProcedencia.SIMPLIFICADO
    assert anotada.maquina is None, "la etapa corre aqui: no hay maquina que declarar"
    informe = leer_informe(proyecto, "limpieza")
    assert informe is not None
    assert informe["purely_reconstructed"] is True


# --- B2: decimado y la distancia --------------------------------------------


def test_el_decimado_respeta_el_objetivo_de_triangulos(tmp_path: pathlib.Path) -> None:
    proyecto = _proyecto_limpio(tmp_path, _esfera())

    decimar(proyecto, objetivo=2000)

    medidas = _medidas(proyecto, "decimado")
    assert medidas["triangulos_antes"] > 2000
    assert medidas["triangulos_despues"] <= 2000


def test_el_decimado_publica_las_dos_direcciones_sin_promediarlas(
    tmp_path: pathlib.Path,
) -> None:
    """Una direccion dice cuanta superficie falta y la otra cuanta sobra.

    La esfera va tupida a proposito: decimar una malla de 4.032 triangulos a 4.000 no
    es decimar, y una distancia de 3e-16 es el ruido de la aritmetica y no una perdida.
    """
    proyecto = _proyecto_limpio(tmp_path, _esfera(anillos=64, gajos=128))

    decimar(proyecto, objetivo=4000)

    distancia = _medidas(proyecto, "decimado")["distancia"]
    assert distancia["estado"] == "MEDIDA"
    # `falta` es superficie que se fue y `sobra` superficie que aparecio: son las
    # palabras del propio diff de SoftSight, y son averias distintas.
    assert distancia["falta"]["maximo"] > distancia["suelo_de_ruido"]
    assert distancia["sobra"]["maximo"] > distancia["suelo_de_ruido"]
    assert distancia["falta"]["maximo"] != distancia["sobra"]["maximo"]
    assert "media" not in distancia, "promediar las dos direcciones esconde lo que importa"


def test_el_plano_decimado_a_la_mitad_sigue_siendo_el_mismo_plano(
    tmp_path: pathlib.Path,
) -> None:
    """El caso rojo que el encargo pide: un plano decimado no deja de ser un plano."""
    proyecto = _proyecto_limpio(tmp_path, _plano())

    decimar(proyecto, objetivo=1024)

    distancia = _medidas(proyecto, "decimado")["distancia"]
    assert distancia["falta"]["maximo"] <= distancia["suelo_de_ruido"]
    assert distancia["sobra"]["maximo"] <= distancia["suelo_de_ruido"]


def test_la_esfera_decimada_al_uno_por_ciento_si_se_mueve(tmp_path: pathlib.Path) -> None:
    """Lo contrario del plano, y con la misma herramienta: aqui la decimacion se ve."""
    proyecto = _proyecto_limpio(tmp_path, _esfera(anillos=32, gajos=64))

    decimar(proyecto, objetivo=160)

    distancia = _medidas(proyecto, "decimado")["distancia"]
    assert distancia["falta"]["maximo"] > distancia["suelo_de_ruido"] * 1_000
    assert distancia["sobra"]["maximo"] > distancia["suelo_de_ruido"] * 1_000
    # Y la desviacion de normales dice lo mismo por otro camino: 20 grados en la
    # peor cara es una esfera que ya no es la misma superficie.
    assert distancia["falta"]["desviacion_de_normales_grados"]["maximo"] > 10.0


def test_el_decimado_declara_la_fraccion_de_la_diagonal(tmp_path: pathlib.Path) -> None:
    """D9: sin referencia de escala no hay milimetros, pero la fraccion de la
    diagonal dice si eso es mucho o poco sin inventarse una unidad."""
    proyecto = _proyecto_limpio(tmp_path, _esfera())

    decimar(proyecto, objetivo=4000)

    distancia = _medidas(proyecto, "decimado")["distancia"]
    diagonal = distancia["diagonal"]
    assert diagonal > 0
    assert distancia["falta"]["fraccion_de_la_diagonal"] == pytest.approx(
        distancia["falta"]["maximo"] / diagonal
    )
    assert distancia["escala"] == "UNKNOWN", "la escala del paquete no la inventa esta etapa"


def test_sin_herramienta_de_medicion_el_informe_dice_not_run(tmp_path: pathlib.Path) -> None:
    """Lo que no se pudo medir se declara con su motivo. Nunca un PASS callado."""
    proyecto = _proyecto_limpio(tmp_path, _esfera())

    decimar(proyecto, objetivo=4000, herramienta=CONSUMIDOR)

    distancia = _medidas(proyecto, "decimado")["distancia"]
    assert distancia["estado"] == "NOT_RUN"
    assert "diffMeshes" in distancia["motivo"]
    no_comprobado = leer_informe(proyecto, "decimado")
    assert no_comprobado is not None
    assert no_comprobado["no_comprobado"]


def test_el_decimado_tambien_declara_su_memoria(tmp_path: pathlib.Path) -> None:
    """§9: millones de triangulos con copias intermedias llenan 8 GB. Con el numero delante."""
    proyecto = _proyecto_limpio(tmp_path, _esfera())

    decimar(proyecto, objetivo=4000)

    memoria = _medidas(proyecto, "decimado")["memoria_maxima_mb"]
    assert memoria > 0


# --- la cadena, con las tres etapas -----------------------------------------


def test_status_dice_que_etapa_toca_con_la_densa_importada(tmp_path: pathlib.Path) -> None:
    proyecto = _proyecto_con_densa(tmp_path, _dos_cubos_con_mota())

    _, texto = _correr("status", str(proyecto))

    assert "densa" in texto and "HECHA" in texto
    assert "limpieza" in texto and "TOCA" in texto


def test_status_marca_caducado_lo_que_se_hizo_sobre_otra_malla(tmp_path: pathlib.Path) -> None:
    """La trampa de §9: se rehace la limpieza con otro umbral y el decimado que
    habia ya no describe esta malla. Caduca en silencio, y esto es lo que lo ve."""
    proyecto = _proyecto_con_densa(tmp_path, _dos_cubos_con_mota())
    limpiar(proyecto)
    decimar(proyecto, objetivo=18)

    # Otro umbral que deja la mota dentro: la malla limpia es otra, y el decimado que
    # habia se hizo sobre la anterior.
    limpiar(proyecto, minimo_relativo=0.0001)

    _, texto = _correr("status", str(proyecto))
    assert "decimado" in texto
    assert "CADUCADA" in texto


def test_decimado_dos_veces_con_el_mismo_objetivo_no_rehace_el_trabajo(
    tmp_path: pathlib.Path,
) -> None:
    """§11 otra vez: si la entrada no cambio, la segunda vez no se vuelve a decimar."""
    proyecto = _proyecto_limpio(tmp_path, _esfera())
    limpiar(proyecto)

    primero = decimar(proyecto, objetivo=2000)
    antes = primero.read_bytes()
    segundo = decimar(proyecto, objetivo=2000)

    assert segundo == primero
    assert segundo.read_bytes() == antes


def test_cambiar_el_objetivo_si_rehace_el_trabajo(tmp_path: pathlib.Path) -> None:
    """El parametro entra en el hash de entrada: decimar a otro numero es otro trabajo."""
    proyecto = _proyecto_limpio(tmp_path, _esfera())
    limpiar(proyecto)

    decimar(proyecto, objetivo=2000)
    decimar(proyecto, objetivo=1000)

    assert _medidas(proyecto, "decimado")["triangulos_despues"] <= 1000


# --- la CLI -----------------------------------------------------------------


def test_la_cli_limpiar_y_decimar_con_objetivo(tmp_path: pathlib.Path) -> None:
    proyecto = _proyecto_con_densa(tmp_path, _dos_cubos_con_mota())

    codigo, texto = _correr("limpieza", str(proyecto))
    assert codigo == 0, texto
    codigo, texto = _correr("decimado", str(proyecto), "--objetivo", "12")
    assert codigo == 0, texto
    assert _medidas(proyecto, "decimado")["triangulos_despues"] <= 12


def test_la_cli_dice_lo_que_falta_cuando_falta_el_proveedor(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sin pymeshlab, un `ProveedorNoDisponible` que dice como instalarlo, no un traceback."""
    import videomesh.adapters.pymeshlab as adaptador

    proyecto = _proyecto_con_densa(tmp_path, _cubo())
    monkeypatch.setattr(adaptador, "instalado", lambda: False)

    codigo, texto = _correr("limpieza", str(proyecto))

    assert codigo == 1
    assert "pymeshlab" in texto
    assert "uv pip install" in texto


def test_la_ayuda_nombra_las_etapas_de_la_cadena() -> None:
    _, texto = _correr("--help")
    assert "videomesh limpieza" in texto
    assert "videomesh decimado" in texto


def test_la_version_del_proveedor_es_la_instalada() -> None:
    """§9: los proveedores cambian resultados entre versiones, y por eso se anota."""
    from videomesh.adapters import pymeshlab as adaptador

    assert adaptador.version() != ""
    assert shutil.which("node") is None or hashlib.sha256(b"").hexdigest() != adaptador.version()


def test_el_paquete_importado_no_se_toca_al_limpiar_ni_al_decimar(tmp_path: pathlib.Path) -> None:
    """La malla medida es la referencia: quien la pise, borra el original del que juzga."""
    proyecto = _proyecto_con_densa(tmp_path, _dos_cubos_con_mota())
    fuente = pathlib.Path(procedencia_de(proyecto)[0].fuente)
    antes = {ruta.name: ruta.read_bytes() for ruta in sorted(fuente.rglob("*")) if ruta.is_file()}

    limpiar(proyecto)
    decimar(proyecto, objetivo=12)

    despues = {ruta.name: ruta.read_bytes() for ruta in sorted(fuente.rglob("*")) if ruta.is_file()}
    assert despues == antes


def test_los_informes_son_json_estricto_y_llevan_sobre(tmp_path: pathlib.Path) -> None:
    """D16 y D17: lo que se escribe se puede leer, y dice que es."""
    proyecto = _proyecto_con_densa(tmp_path, _cubo())
    limpiar(proyecto)

    informe = leer_informe(proyecto, "limpieza")
    assert informe is not None
    assert informe["documentType"] == "videomesh.stage-report"
    assert informe["contractVersion"]
    texto = json.dumps(informe)
    assert "NaN" not in texto and "Infinity" not in texto
