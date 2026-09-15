"""B3 — D11: cada transformacion entre marcos queda registrada, y se comprueba.

El grafo estaba en el esquema desde R0-A y nadie lo miraba: un paquete podia
declarar cero aristas y salir COMPLETE + PASS. El campo se rellenaba por
educacion, «que es la forma que tiene una decision de parecer cumplida».

Lo que lo convierte en registro no es que haya transformaciones declaradas —eso se
cumple rellenando una lista— sino que **un marco al que no hay camino se rechaza**.
Y desde RECONSTRUCTION, porque es donde estan los numeros: las cajas y los
volumenes salen del PLY, que viene en ese marco.
"""

import json
import math
from typing import Any

import pytest

from videomesh.contracts.generacion import ESQUEMAS
from videomesh.domain.algebra import IDENTIDAD, componer, inversa_rigida
from videomesh.domain.frames import (
    ErrorDeMarco,
    comprobar_frame_graph,
    resolver_marco,
)

MANIFEST = json.loads(
    (ESQUEMAS.parent / "artifacts" / "cube-v1" / "manifest.json").read_text(encoding="utf-8")
)

CASOS_DE_TRANSFORMACION = json.loads(
    (ESQUEMAS / "fixtures" / "transform-gltf-v1.json").read_text(encoding="utf-8")
)["cases"]

#: Una rotacion de verdad, del tercer caso de `transform-gltf-v1`. Las otras tres
#: del fixture llevan escala dentro, asi que no son transformaciones entre marcos.
ROTACION = CASOS_DE_TRANSFORMACION[2]["canonicalByRows"]
TRASLACION = [
    1.0, 0.0, 0.0, 5.0,
    0.0, 1.0, 0.0, 6.0,
    0.0, 0.0, 1.0, 7.0,
    0.0, 0.0, 0.0, 1.0,
]  # fmt: skip


def _arista(origen: str, destino: str, matriz: list[float]) -> dict[str, Any]:
    return {
        "from": origen,
        "to": destino,
        "matrix": matriz,
        "reason": "prueba",
        "producer": "videomesh/pruebas",
    }


DOS_SALTOS = [
    _arista("RECONSTRUCTION", "ASSET_CANONICAL", ROTACION),
    _arista("ASSET_CANONICAL", "PRODUCTION", TRASLACION),
]


def test_el_frame_graph_de_cube_v1_se_acepta() -> None:
    comprobar_frame_graph(MANIFEST["frameGraph"]["transforms"])


#: Lo que D11 llama identidad «exacta» **no se puede exigir bit a bit** y conviene
#: decir por que. La rotacion de 90 grados del propio fixture trae dentro
#: 1.0000000000000002 y -2.22e-16, asi que no es exactamente ortonormal: `R^T R` ya
#: no da la identidad antes de que este codigo toque nada. La tolerancia es esa —el
#: ultimo bit de un doble— y va declarada, no supuesta.
TOLERANCIA_IDENTIDAD = 1e-15


def test_la_ida_y_vuelta_por_dos_saltos_da_la_identidad() -> None:
    """Lo que cierra D11, con la tolerancia que la aritmetica permite."""
    ida = resolver_marco(DOS_SALTOS, "RECONSTRUCTION", "PRODUCTION")
    vuelta = resolver_marco(DOS_SALTOS, "PRODUCTION", "RECONSTRUCTION")
    vuelto = componer(vuelta, ida)
    assert all(
        math.isclose(a, b, abs_tol=TOLERANCIA_IDENTIDAD)
        for a, b in zip(vuelto, IDENTIDAD, strict=True)
    )


def test_con_una_rotacion_exacta_la_ida_y_vuelta_si_es_bit_a_bit() -> None:
    """Acota de donde viene el error: del dato declarado, no del recorrido.

    Con una matriz exactamente ortonormal —ceros y unos— la vuelta deshace la ida
    sin perder un bit. La inversa se escribe como `R^T` y `-R^T t`, sin ninguna
    division, asi que no hay nada que redondee. Lo que no es exacto es la rotacion
    que el fixture declara.
    """
    exacta = [
        0.0, -1.0, 0.0, 0.0,
        1.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]  # fmt: skip
    grafo = [
        _arista("RECONSTRUCTION", "ASSET_CANONICAL", exacta),
        _arista("ASSET_CANONICAL", "PRODUCTION", TRASLACION),
    ]
    ida = resolver_marco(grafo, "RECONSTRUCTION", "PRODUCTION")
    vuelta = resolver_marco(grafo, "PRODUCTION", "RECONSTRUCTION")
    assert componer(vuelta, ida) == [float(x) for x in IDENTIDAD]


def test_las_aristas_se_recorren_en_los_dos_sentidos() -> None:
    """Declarar las dos direcciones seria el mismo dato dos veces esperando a divergir."""
    vuelta = resolver_marco(DOS_SALTOS, "ASSET_CANONICAL", "RECONSTRUCTION")
    esperada = inversa_rigida(ROTACION)
    assert all(
        math.isclose(a, b, abs_tol=TOLERANCIA_IDENTIDAD)
        for a, b in zip(vuelta, esperada, strict=True)
    )


def test_un_marco_sin_camino_no_devuelve_la_identidad_sino_un_error() -> None:
    """Suponer que dos marcos sin arista son el mismo es el error, no su arreglo."""
    suelto = [_arista("RECONSTRUCTION", "ASSET_CANONICAL", IDENTIDAD)]
    with pytest.raises(ErrorDeMarco, match="MARCO_INALCANZABLE"):
        resolver_marco(suelto, "RECONSTRUCTION", "PRODUCTION")


def test_una_arista_no_rigida_se_rechaza_por_su_nombre() -> None:
    """Ultima fila distinta de [0,0,0,1]: lleva proyeccion dentro y no es una pose."""
    con_proyeccion = list(IDENTIDAD)
    con_proyeccion[14] = -0.5
    with pytest.raises(ErrorDeMarco, match="TRANSFORMACION_NO_RIGIDA"):
        comprobar_frame_graph([_arista("RECONSTRUCTION", "PRODUCTION", con_proyeccion)])


@pytest.mark.parametrize(
    "caso",
    [pytest.param(c, id=c["name"]) for c in CASOS_DE_TRANSFORMACION if "escala" in c["name"]],
)
def test_una_arista_con_escala_tampoco_es_rigida(caso: dict[str, Any]) -> None:
    """Una escala tiene inversa, pero no la exacta que D11 necesita para ir y volver.

    Los tres casos salen del propio `transform-gltf-v1`: son matrices 4x4 validas
    y correctas como transformacion, y aun asi no son transformaciones entre
    marcos. Es lo que separa «la matriz esta bien» de «esto es una pose».
    """
    with pytest.raises(ErrorDeMarco, match="TRANSFORMACION_NO_RIGIDA"):
        comprobar_frame_graph([_arista("RECONSTRUCTION", "PRODUCTION", caso["canonicalByRows"])])


def test_una_arista_de_un_marco_a_si_mismo_se_rechaza() -> None:
    with pytest.raises(ErrorDeMarco, match="TRANSFORMACION_MAL_FORMADA"):
        comprobar_frame_graph([_arista("RECONSTRUCTION", "RECONSTRUCTION", IDENTIDAD)])


def test_una_arista_duplicada_se_rechaza() -> None:
    """Dos matrices para el mismo salto son dos respuestas a la misma pregunta."""
    arista = _arista("RECONSTRUCTION", "ASSET_CANONICAL", IDENTIDAD)
    with pytest.raises(ErrorDeMarco, match="TRANSFORMACION_MAL_FORMADA"):
        comprobar_frame_graph([arista, dict(arista, matrix=list(TRASLACION))])


def test_la_misma_arista_declarada_al_reves_tambien_es_duplicada() -> None:
    """El grafo ya recorre en los dos sentidos: declararlo es el dato dos veces."""
    with pytest.raises(ErrorDeMarco, match="TRANSFORMACION_MAL_FORMADA"):
        comprobar_frame_graph(
            [
                _arista("RECONSTRUCTION", "ASSET_CANONICAL", IDENTIDAD),
                _arista("ASSET_CANONICAL", "RECONSTRUCTION", IDENTIDAD),
            ]
        )


def test_un_marco_declarado_al_que_no_se_llega_desde_reconstruction_se_rechaza() -> None:
    """Es lo que separa un registro de una lista rellenada por educacion."""
    isla = [
        _arista("RECONSTRUCTION", "ASSET_CANONICAL", IDENTIDAD),
        _arista("CAMERA", "PRODUCTION", IDENTIDAD),
    ]
    with pytest.raises(ErrorDeMarco, match="MARCO_INALCANZABLE"):
        comprobar_frame_graph(isla)


def test_un_grafo_sin_ninguna_arista_se_acepta_solo_si_no_declara_marcos() -> None:
    """Cero aristas no es un error por si mismo; lo es declarar un marco y no llegar."""
    comprobar_frame_graph([])


def test_un_marco_que_no_existe_se_rechaza() -> None:
    with pytest.raises(ErrorDeMarco, match="MARCO_DESCONOCIDO"):
        comprobar_frame_graph([_arista("RECONSTRUCTION", "MUNDO", IDENTIDAD)])
