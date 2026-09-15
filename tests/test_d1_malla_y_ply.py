"""D1, primera pieza — la geometria del cubo y su PLY.

`cube-v1` se **fabrica**, no se reconstruye: la reconstruccion es del Sprint 2. Lo
que tiene que salir esta en los valores dorados de `package-parity-v1`:

    24 vertices · 12 triangulos · 8 soldados · nube de 8 puntos · caja +-0,5

24 y 8 no se contradicen: cada esquina aparece tres veces, una por cara, porque
las normales por cara no se pueden compartir. Un lector que suelde al leer daria 8
y **no estaria mal** — son dos preguntas distintas, y por eso van las dos.
"""

import json
import pathlib

import pytest

from videomesh.contracts.generacion import ESQUEMAS
from videomesh.domain.malla import caja_envolvente, cubo_unidad, esquinas_del_cubo, soldar
from videomesh.formatos.ply import escribir_ply_malla, escribir_ply_nube, leer_cabecera_ply

DORADOS = json.loads((ESQUEMAS / "fixtures" / "package-parity-v1.json").read_text())["recuentos"][
    "cube-v1"
]
CAJA = json.loads((ESQUEMAS / "fixtures" / "package-parity-v1.json").read_text())["caja"]["cube-v1"]


def test_el_cubo_tiene_los_vertices_y_triangulos_dorados() -> None:
    malla = cubo_unidad()
    assert len(malla.vertices) == DORADOS["malla"]["vertices"]
    assert len(malla.triangulos) == DORADOS["malla"]["triangulos"]


def test_soldar_los_vertices_da_las_ocho_esquinas() -> None:
    """La otra pregunta: cuantas posiciones distintas hay, no cuantas entradas."""
    assert len(soldar(cubo_unidad().vertices)) == DORADOS["malla"]["verticesSoldados"]


def test_la_nube_dispersa_son_las_ocho_esquinas() -> None:
    assert len(esquinas_del_cubo()) == DORADOS["nube"]["puntos"]


def test_la_caja_del_cubo_es_la_dorada() -> None:
    minimo, maximo = caja_envolvente(cubo_unidad().vertices)
    assert minimo == CAJA["malla"]["min"]
    assert maximo == CAJA["malla"]["max"]


def test_todos_los_triangulos_apuntan_hacia_fuera() -> None:
    """Una cara al reves da un cubo que por dentro parece cerrado y por fuera no.

    Con el centro en el origen, la normal de cada cara tiene que apartarse de el.
    """
    malla = cubo_unidad()
    for a, b, c in malla.triangulos:
        pa, pb, pc = malla.vertices[a], malla.vertices[b], malla.vertices[c]
        u = [pb[i] - pa[i] for i in range(3)]
        v = [pc[i] - pa[i] for i in range(3)]
        normal = [
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        ]
        centro = [(pa[i] + pb[i] + pc[i]) / 3 for i in range(3)]
        assert sum(n * c for n, c in zip(normal, centro, strict=True)) > 0


def test_cada_arista_la_comparten_exactamente_dos_triangulos() -> None:
    """Es lo que quiere decir cerrada. Sin esto, el cubo tendria agujeros invisibles."""
    malla = cubo_unidad()
    posiciones = {i: malla.vertices[i] for i in range(len(malla.vertices))}
    aristas: dict[frozenset[tuple[float, ...]], int] = {}
    for triangulo in malla.triangulos:
        for i in range(3):
            arista = frozenset(
                (
                    tuple(posiciones[triangulo[i]]),
                    tuple(posiciones[triangulo[(i + 1) % 3]]),
                )
            )
            aristas[arista] = aristas.get(arista, 0) + 1
    assert set(aristas.values()) == {2}


def test_el_ply_declara_lo_que_lleva(tmp_path: pathlib.Path) -> None:
    destino = tmp_path / "mesh.ply"
    escribir_ply_malla(destino, cubo_unidad())
    cabecera = leer_cabecera_ply(destino)
    assert cabecera["vertex"] == 24
    assert cabecera["face"] == 12


def test_el_ply_de_la_nube_no_declara_caras(tmp_path: pathlib.Path) -> None:
    destino = tmp_path / "sparse.ply"
    escribir_ply_nube(destino, esquinas_del_cubo())
    cabecera = leer_cabecera_ply(destino)
    assert cabecera["vertex"] == 8
    assert "face" not in cabecera


def test_el_ply_es_determinista(tmp_path: pathlib.Path) -> None:
    """Dos generaciones dan los mismos bytes, o `expected.json` no significa nada."""
    primero, segundo = tmp_path / "a.ply", tmp_path / "b.ply"
    escribir_ply_malla(primero, cubo_unidad())
    escribir_ply_malla(segundo, cubo_unidad())
    assert primero.read_bytes() == segundo.read_bytes()


def test_el_ply_no_escribe_notacion_cientifica(tmp_path: pathlib.Path) -> None:
    """Un `1e-17` en un PLY lo lee cualquiera, pero no todos los lectores igual."""
    destino = tmp_path / "mesh.ply"
    escribir_ply_malla(destino, cubo_unidad())
    texto = destino.read_text(encoding="ascii")
    assert "e-" not in texto
    assert "e+" not in texto


def test_un_ply_con_un_no_finito_no_se_escribe(tmp_path: pathlib.Path) -> None:
    """D17 tambien aqui: el PLY no es JSON, pero un infinito sigue sin ser una medida."""
    from videomesh.domain.malla import Malla

    rota = Malla(vertices=[(0.0, 0.0, float("inf"))] * 3, triangulos=[(0, 1, 2)])
    with pytest.raises(ValueError, match="finito"):
        escribir_ply_malla(tmp_path / "mesh.ply", rota)
