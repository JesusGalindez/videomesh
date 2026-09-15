"""VideoMesh declara la combinacion entera de versiones que habla — D12.

«El consumidor comprueba el bloque, no un campo.» El motivo no es estetico: el
2026-09-14 `reconstructionReport` subio de 0.1 a 0.2 despues de cambiar seis veces
con el numero quieto. Una constante suelta que diga `0.1` sigue siendo correcta
**por casualidad**, y el dia que el paquete suba mentira sin que nada lo vea.

`versions.json` de SoftSight no se copia aqui. Se lee del original: una copia
diverge, que es el error que el symlink del contrato ya evita.
"""

import json
import pathlib

import pytest

from videomesh.contracts.estado import (
    ErrorDeCombinacion,
    combinacion_declarada,
    combinaciones_admitidas,
    comprobar_combinacion,
    estado_generado,
    version_del_paquete,
)
from videomesh.contracts.generacion import ESQUEMAS

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ESTADO = RAIZ / "contracts" / "estado.json"
REGISTRO = json.loads((ESQUEMAS / "versions.json").read_text(encoding="utf-8"))


def test_el_estado_declara_la_combinacion_entera_y_no_versiones_sueltas() -> None:
    declarados = set(combinacion_declarada())
    esperados = {contrato["name"] for contrato in REGISTRO["contracts"]}
    assert declarados == esperados


def test_la_combinacion_declarada_es_una_de_las_que_softsight_admite() -> None:
    comprobar_combinacion(combinacion_declarada(), combinaciones_admitidas())


def test_una_combinacion_que_nadie_ha_declarado_se_rechaza() -> None:
    """El caso que hace que la prueba valga: cada numero existe, juntos no."""
    inventada = dict(combinacion_declarada(), reconstructionReport="0.1")
    with pytest.raises(ErrorDeCombinacion) as capturado:
        comprobar_combinacion(inventada, combinaciones_admitidas())
    assert "reconstructionReport" in str(capturado.value)


def test_un_bloque_al_que_le_falta_un_contrato_se_rechaza() -> None:
    """D12. Faltar no es hablar menos: es no decir que se habla."""
    incompleta = {k: v for k, v in combinacion_declarada().items() if k != "bridge"}
    with pytest.raises(ErrorDeCombinacion, match="bridge"):
        comprobar_combinacion(incompleta, combinaciones_admitidas())


def test_un_contrato_de_mas_tambien_se_rechaza() -> None:
    """Declarar uno que el registro no conoce es declarar que se habla algo inexistente."""
    de_mas = dict(combinacion_declarada(), contratoQueNadieConoce=1)
    with pytest.raises(ErrorDeCombinacion, match="contratoQueNadieConoce"):
        comprobar_combinacion(de_mas, combinaciones_admitidas())


def test_una_version_subida_sin_regenerar_el_fichero_se_rechaza() -> None:
    """La otra mitad de la puerta de D12: lo commiteado tiene que estar al dia."""
    assert ESTADO.read_text(encoding="utf-8") == estado_generado()


def test_la_version_del_paquete_sale_del_bloque_y_no_de_una_constante() -> None:
    assert version_del_paquete() == combinacion_declarada()["reconstructionPackage"]


def test_no_queda_ninguna_constante_suelta_con_la_version_del_contrato() -> None:
    """Dos fuentes del mismo numero divergen en la primera subida.

    Se vigila igual que D32 vigila su formula: el fallo no rompe ninguna prueba el
    dia que se escribe, solo el dia que los dos numeros dejan de coincidir.
    """
    codigo = RAIZ / "src" / "videomesh"
    lo_declaran = {
        ruta.relative_to(codigo).as_posix()
        for ruta in codigo.rglob("*.py")
        if "CONTRACT_VERSION" in ruta.read_text(encoding="utf-8")
    }
    assert lo_declaran == set()
