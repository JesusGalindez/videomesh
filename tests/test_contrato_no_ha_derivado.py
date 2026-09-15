"""La tabla de obligaciones declara contra que contrato se escribio. Aqui se comprueba.

El mecanismo estaba escrito en la cabecera del propio documento desde el primer
dia —«se comprueba con `shasum -a 256`»— y **no sirvio de nada porque nadie lo
ejecuto**: un mes despues la tabla tenia nueve filas caducadas y cuatro nombres de
fixture que no existian.

Un aviso que depende de que alguien se acuerde no es una puerta. Esto si.
"""

import hashlib
import pathlib

import pytest

from videomesh.contracts.deriva import (
    ErrorDeDeriva,
    comprobar_hash_declarado,
    hash_declarado_en,
)

RAIZ = pathlib.Path(__file__).resolve().parents[1]
OBLIGACIONES = RAIZ / "docs" / "OBLIGACIONES-VIDEOMESH.md"
CONTRATO = RAIZ / "docs" / "contrato-videomesh.md"


def test_el_hash_declarado_es_el_del_contrato_de_hoy() -> None:
    comprobar_hash_declarado(
        OBLIGACIONES.read_text(encoding="utf-8"),
        hashlib.sha256(CONTRATO.read_bytes()).hexdigest(),
    )


def test_la_cabecera_declara_algo_con_forma_de_sha256() -> None:
    """Un texto cualquiera colado ahi haria que la comparacion nunca cuadrara."""
    declarado = hash_declarado_en(OBLIGACIONES.read_text(encoding="utf-8"))
    assert len(declarado) == 64
    assert set(declarado) <= set("0123456789abcdef")


def test_un_hash_declarado_que_no_cuadra_pone_esto_en_rojo() -> None:
    """El caso que hace que la prueba valga. Se ejerce sin tocar el documento.

    Los numeros son los de verdad: `6dc06081…` es el contrato del 2026-08-12 que
    la tabla declaro durante un mes, y `b9e0e708…` el de hoy.
    """
    cabecera_vieja = "sha256 `6dc060810000000000000000000000000000000000000000000000000000dead`"
    with pytest.raises(ErrorDeDeriva) as capturado:
        comprobar_hash_declarado(cabecera_vieja, "b9e0e708" + "0" * 56)
    mensaje = str(capturado.value)
    assert "6dc06081" in mensaje
    assert "b9e0e708" in mensaje
    # Lo que importa del mensaje no es que no cuadre: es que diga que hacer.
    assert "OBLIGACIONES-VIDEOMESH.md" in mensaje


def test_un_documento_sin_hash_en_la_cabecera_se_rechaza() -> None:
    """Borrar la linea no puede ser la forma de pasar la puerta."""
    with pytest.raises(ErrorDeDeriva):
        hash_declarado_en("# Obligaciones\n\nsin hash ninguno\n")


def test_la_puerta_no_se_conforma_con_encontrar_el_hash_en_cualquier_sitio() -> None:
    """Si valiera cualquier sha256 del documento, la tabla podria citar otro fichero."""
    with pytest.raises(ErrorDeDeriva):
        hash_declarado_en("# Obligaciones\n\nel PLY pesa `" + "a" * 64 + "`\n")
