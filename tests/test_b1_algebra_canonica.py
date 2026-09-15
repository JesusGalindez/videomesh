"""B1 — V9 y D32: 4x4 por filas, traslacion en 3, 7 y 11, vectores columna.

No es la convencion de glTF y **no son intercambiables**. La conversion ocurre
exactamente una vez, en el adaptador de frontera.

La prueba es el fixture `transform-gltf-v1` de SoftSight, consumido desde aqui.
Lo decisivo de ese fichero no son las matrices: es la ultima columna, **un punto
conocido a su punto transformado conocido**, calculado fuera del repositorio. Una
ida y vuelta no vale porque dos transposiciones se cancelan y el documento vuelve
identico con el punto en otro sitio — que es literalmente el fallo que D32
describe.
"""

import json
import math
import pathlib
from typing import Any

import pytest

from videomesh.adapters.gltf_transforms import a_gltf, de_gltf
from videomesh.contracts.generacion import ESQUEMAS
from videomesh.domain.algebra import aplicar, inversa_rigida

FIXTURE = json.loads((ESQUEMAS / "fixtures" / "transform-gltf-v1.json").read_text(encoding="utf-8"))
CASOS = [pytest.param(c, id=c["name"]) for c in FIXTURE["cases"]]

#: Tolerancia declarada, no supuesta. Los numeros del fixture se calcularon fuera
#: con doble precision; lo que se compara es el mismo calculo, no un redondeo.
TOLERANCIA = 1e-12


def _iguales(obtenido: list[float], esperado: list[float]) -> bool:
    return len(obtenido) == len(esperado) and all(
        math.isclose(a, b, rel_tol=TOLERANCIA, abs_tol=TOLERANCIA)
        for a, b in zip(obtenido, esperado, strict=True)
    )


@pytest.mark.parametrize("caso", CASOS)
def test_el_punto_conocido_llega_a_su_punto_conocido(caso: dict[str, Any]) -> None:
    """Lo unico que caza una transposicion de mas."""
    assert _iguales(aplicar(caso["canonicalByRows"], caso["point"]), caso["expected"])


@pytest.mark.parametrize("caso", CASOS)
def test_la_matriz_de_gltf_se_lee_a_la_canonica(caso: dict[str, Any]) -> None:
    assert _iguales(de_gltf(caso["gltfMatrixByColumns"]), caso["canonicalByRows"])


@pytest.mark.parametrize("caso", CASOS)
def test_la_canonica_se_escribe_a_la_de_gltf(caso: dict[str, Any]) -> None:
    assert _iguales(a_gltf(caso["canonicalByRows"]), caso["gltfMatrixByColumns"])


@pytest.mark.parametrize("caso", CASOS)
def test_la_ida_y_vuelta_es_identica_y_por_eso_no_basta(caso: dict[str, Any]) -> None:
    """Se comprueba, pero se sabe que no prueba nada por si sola: ver el caso oblicuo."""
    assert _iguales(de_gltf(a_gltf(caso["canonicalByRows"])), caso["canonicalByRows"])


def test_el_punto_aplicado_como_fila_se_va_a_donde_D32_dice() -> None:
    """La trampa que hace util al fixture. Sin ella, la ida y vuelta pasaria igual.

    D32 publica tres numeros para este fallo —(-0,486, -0,735, 1,803)— y son los
    de aplicar el punto **como fila** en vez de como columna: la otra convencion
    de vectores. Es el error que ninguna ida y vuelta ve, porque la matriz no se
    toca; lo que cambia es por que lado se multiplica.
    """
    oblicuo = FIXTURE["cases"][-1]
    matriz, punto = oblicuo["canonicalByRows"], oblicuo["point"]
    como_fila = [
        sum(([*punto, 1])[k] * matriz[k * 4 + columna] for k in range(4)) for columna in range(3)
    ]
    assert [round(x, 3) for x in como_fila] == [-0.486, -0.735, 1.803]
    assert not _iguales(como_fila, oblicuo["expected"])


def test_una_matriz_de_gltf_sin_transponer_se_rechaza_en_vez_de_dar_un_punto() -> None:
    """Por columnas la traslacion vive en 12, 13 y 14: leida por filas, la ultima fila.

    Ahi no mueve el punto, pero hace que `w` deje de valer 1. Dividir por ese `w`
    devolveria un punto plausible y equivocado — el fallo de D32 disfrazado de
    medida. Aqui se rechaza.
    """
    oblicuo = FIXTURE["cases"][-1]
    with pytest.raises(ValueError, match="ultima fila"):
        aplicar(oblicuo["gltfMatrixByColumns"], oblicuo["point"])


def test_la_traslacion_vive_en_3_7_y_11() -> None:
    """Donde este la traslacion no es un detalle de formato: decide que mueve que."""
    canonica = FIXTURE["cases"][0]["canonicalByRows"]
    assert [canonica[3], canonica[7], canonica[11]] == [5, 6, 7]


def test_una_matriz_que_no_es_de_dieciseis_numeros_se_rechaza() -> None:
    with pytest.raises(ValueError):
        aplicar([1, 0, 0, 0], [1, 2, 3])


def test_la_conversion_a_gltf_vive_en_un_solo_sitio() -> None:
    """La puerta que impide que vuelva la deuda: dos transposiciones se cancelan.

    Es la misma que `test:gltf-frame` del otro lado, que comprueba que
    `column * 4 + row` no aparece en `src/` fuera de un fichero. En SoftSight eran
    tres copias, no dos, y la geometria salia bien colocada por casualidad sin que
    ningun hash lo delatara.

    Dos ficheros tienen derecho a escribir esa forma, y conviene decir por que son
    operaciones distintas aunque se escriban igual:

    - `adapters/gltf_transforms.py` transpone la matriz **entera**, que es la
      conversion de convencion. Solo ahi.
    - `domain/algebra.py` transpone la **rotacion 3x3** para invertir una
      transformacion rigida, y ademas niega la traslacion. No es la misma matriz
      de salida, y `test_la_inversa_rigida_no_es_la_transpuesta` lo comprueba con
      numeros en vez de con confianza.

    Un tercer fichero con esta forma es deuda y esta puerta lo dice.
    """
    codigo = pathlib.Path(__file__).resolve().parents[1] / "src" / "videomesh"
    con_gltf = {
        ruta.relative_to(codigo).as_posix()
        for ruta in codigo.rglob("*.py")
        if "columna * 4 + fila" in ruta.read_text(encoding="utf-8")
    }
    assert con_gltf == {"adapters/gltf_transforms.py", "domain/algebra.py"}


def test_la_inversa_rigida_no_es_la_transpuesta_de_la_matriz() -> None:
    """Lo que separa las dos transposiciones, dicho con numeros.

    Si fueran la misma operacion, esta prueba pasaria — y entonces el dominio
    estaria haciendo por dentro la conversion que D32 manda hacer una sola vez en
    el adaptador.
    """
    con_traslacion = [
        1.0, 0.0, 0.0, 5.0,
        0.0, 1.0, 0.0, 6.0,
        0.0, 0.0, 1.0, 7.0,
        0.0, 0.0, 0.0, 1.0,
    ]  # fmt: skip
    assert inversa_rigida(con_traslacion) != a_gltf(con_traslacion)
    # La inversa deshace; la transpuesta manda la traslacion a la ultima fila.
    assert inversa_rigida(con_traslacion)[3:12:4] == [-5.0, -6.0, -7.0]
    assert a_gltf(con_traslacion)[12:15] == [5.0, 6.0, 7.0]
