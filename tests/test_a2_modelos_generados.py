"""A2 — D15: los modelos salen del esquema publicado, nunca de la mano.

Un modelo escrito a mano es un segundo original: diverge en el primer campo nuevo
y nadie se entera hasta que el paquete viaja. El envio 02 metio cuatro campos
obligatorios de golpe.

La puerta es la misma idea que `contracts --check` de SoftSight: se regenera y se
compara con lo commiteado. Si el esquema cambia y los modelos no, rojo.
"""

import json
import pathlib

import pytest
from pydantic import ValidationError

from videomesh.contracts.generacion import ESQUEMAS, generar_modulos
from videomesh.contracts.modelos import ReconstructionPackage

RAIZ = pathlib.Path(__file__).resolve().parents[1]
GENERADOS = RAIZ / "src" / "videomesh" / "contracts" / "modelos"
MANIFEST_CUBE_V1 = ESQUEMAS.parent / "artifacts" / "cube-v1" / "manifest.json"


def test_hay_ocho_esquemas_publicados() -> None:
    """Si SoftSight publica uno mas, esta prueba lo dice antes que nadie."""
    assert len(sorted(ESQUEMAS.glob("*.schema.json"))) == 8


@pytest.mark.parametrize("nombre", sorted(generar_modulos()))
def test_lo_commiteado_es_exactamente_lo_que_sale_del_esquema(nombre: str) -> None:
    esperado = generar_modulos()[nombre]
    fichero = GENERADOS / nombre
    assert fichero.exists(), f"falta {fichero}; regenera con scripts/generar_modelos.py"
    assert fichero.read_text(encoding="utf-8") == esperado


def test_el_manifest_real_de_softsight_valida_contra_los_modelos() -> None:
    """La prueba de que el modelo describe el contrato de verdad, no una lectura suya."""
    crudo = json.loads(MANIFEST_CUBE_V1.read_text(encoding="utf-8"))
    paquete = ReconstructionPackage.model_validate(crudo)
    assert paquete.packageId == "cube-v1"
    assert len(paquete.cameras or []) == 4


def test_un_campo_desconocido_en_el_nucleo_se_rechaza() -> None:
    """D30: fuera de `extensions`, un campo que nadie conoce es error, no aviso."""
    crudo = json.loads(MANIFEST_CUBE_V1.read_text(encoding="utf-8"))
    crudo["campoQueNadieConoce"] = 1
    with pytest.raises(ValidationError):
        ReconstructionPackage.model_validate(crudo)


def test_la_ida_y_vuelta_no_inventa_ni_pierde_campos() -> None:
    """Si el modelo reordena o rellena, el paquete que salga ya no es el que entro."""
    crudo = json.loads(MANIFEST_CUBE_V1.read_text(encoding="utf-8"))
    devuelto = ReconstructionPackage.model_validate(crudo).model_dump(
        by_alias=True, exclude_none=True
    )
    assert devuelto == crudo


def test_una_construccion_que_el_generador_no_entiende_falla_en_voz_alta() -> None:
    """El dia que SoftSight publique un `$ref`, esto tiene que parar la generacion.

    La alternativa —emitir un modelo que se salta lo que no entiende— es un modelo
    que dice que valida y no valida.
    """
    from videomesh.contracts.generacion import ErrorDeEsquema, _Generador

    with pytest.raises(ErrorDeEsquema):
        _Generador("prueba").tipo({"$ref": "#/$defs/algo"}, [])


def test_un_objeto_que_no_cierra_sus_campos_no_se_genera() -> None:
    """D30: el nucleo se cierra. Un modelo abierto acepta en silencio lo que deberia rechazar."""
    from videomesh.contracts.generacion import ErrorDeEsquema, _Generador

    abierto = {"type": "object", "properties": {"a": {"type": "string"}}}
    with pytest.raises(ErrorDeEsquema):
        _Generador("prueba").tipo(abierto, [])
