"""A1 — V1 y V2: ninguna serializacion de este repositorio emite un no finito.

D17. El rechazo es **en origen**: no se confia en que Node lo cace despues. Y no
basta con vigilar la palabra `NaN`, porque nadie la escribe y el infinito entra
igual — `JSON.parse('{"bytes": 1e999}')` da `Infinity` sin que aparezca en el
texto.
"""

import math

import pytest

from videomesh.contracts.serialization import ErrorNumeroNoFinito, volcar_json


@pytest.mark.parametrize(
    ("nombre", "valor"),
    [("NaN", math.nan), ("Infinity", math.inf), ("-Infinity", -math.inf)],
)
def test_json_rejects_non_finite_numbers(nombre: str, valor: float) -> None:
    """Los tres no finitos fallan en origen, no en el consumidor."""
    with pytest.raises(ErrorNumeroNoFinito) as capturado:
        volcar_json({"medida": valor})
    assert nombre in str(capturado.value)


def test_el_error_dice_donde_esta_el_no_finito() -> None:
    """Un mensaje que no dice el campo obliga a buscarlo a mano en una matriz de 16."""
    with pytest.raises(ErrorNumeroNoFinito) as capturado:
        volcar_json({"camaras": [{"id": "cam-frontal", "worldFromCamera": [1.0, math.inf]}]})
    assert "camaras[0].worldFromCamera[1]" in str(capturado.value)


def test_el_no_finito_se_caza_dentro_de_una_clave() -> None:
    """Las claves tambien se serializan; una clave no finita saldria como texto valido."""
    with pytest.raises(ErrorNumeroNoFinito):
        volcar_json({math.inf: 1})


def test_un_literal_desbordado_tambien_es_infinito() -> None:
    """1e999 no contiene la palabra y es Infinity igual. El agujero medido el 2026-08-12."""
    with pytest.raises(ErrorNumeroNoFinito):
        volcar_json({"bytes": float("1e999")})


def test_un_documento_finito_se_serializa_en_forma_canonica() -> None:
    """Claves ordenadas y sin espacios: dos generaciones iguales dan bytes iguales (V4)."""
    assert volcar_json({"b": 2, "a": [1.5, -0.0]}) == '{"a":[1.5,-0.0],"b":2}'


def test_los_booleanos_no_se_confunden_con_numeros() -> None:
    """bool es subclase de int en Python; comprobar finitud sobre el no debe romperlo."""
    assert volcar_json({"cerrada": True, "vacia": None}) == '{"cerrada":true,"vacia":null}'
