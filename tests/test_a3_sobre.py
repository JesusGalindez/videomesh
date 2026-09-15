"""A3 — D16: todo lo que se escriba lleva sobre, y se comprueba antes de disco.

`documentType`, `contractVersion` y `contractSchemaSha256`. Los tres se
comprueban **en el escritor**: un manifest sin sobre no llega a escribirse. Que lo
rechace el consumidor llega tarde, porque para entonces el paquete ya esta en
disco y sellado.

El hash no se copia a mano. D16 reparte la autoridad: el esquema es el artefacto,
el registro es la busqueda por hash, y el sobre se **genera** de los dos.
"""

import json

import pytest

from videomesh.contracts.generacion import ESQUEMAS
from videomesh.contracts.sobre import (
    PAQUETE_DE_RECONSTRUCCION,
    ErrorDeSobre,
    sobre_de,
    volcar_documento,
)

REGISTRO = json.loads((ESQUEMAS / "registry.json").read_text(encoding="utf-8"))
MANIFEST_CUBE_V1 = json.loads(
    (ESQUEMAS.parent / "artifacts" / "cube-v1" / "manifest.json").read_text(encoding="utf-8")
)


def test_el_sobre_trae_los_tres_campos() -> None:
    assert set(sobre_de(PAQUETE_DE_RECONSTRUCCION)) == {
        "documentType",
        "contractVersion",
        "contractSchemaSha256",
    }


def test_el_hash_del_sobre_es_el_del_esquema_publicado_hoy() -> None:
    """Si se copiara a mano, envejeceria en silencio en cuanto cambiara el esquema."""
    registrado = next(e for e in REGISTRO["schemas"] if e["name"] == "reconstruction-package")
    assert sobre_de(PAQUETE_DE_RECONSTRUCCION)["contractSchemaSha256"] == registrado["sha256"]


def test_la_version_del_sobre_es_una_de_las_que_el_consumidor_acepta() -> None:
    assert sobre_de(PAQUETE_DE_RECONSTRUCCION)["contractVersion"] in REGISTRO["contractVersions"]


@pytest.mark.parametrize("ausente", ["documentType", "contractVersion"])
def test_un_documento_sin_sobre_no_se_escribe(ausente: str) -> None:
    documento = dict(MANIFEST_CUBE_V1)
    del documento[ausente]
    with pytest.raises(ErrorDeSobre) as capturado:
        volcar_documento(documento)
    assert ausente in str(capturado.value)


def test_un_hash_de_esquema_que_el_registro_no_conoce_se_rechaza_aqui() -> None:
    """ESQUEMA_NO_COINCIDE del otro lado. Mejor pararlo antes de escribir el paquete."""
    documento = dict(MANIFEST_CUBE_V1, contractSchemaSha256="00" * 32)
    with pytest.raises(ErrorDeSobre):
        volcar_documento(documento)


def test_una_version_de_contrato_fuera_de_las_aceptadas_se_rechaza() -> None:
    documento = dict(MANIFEST_CUBE_V1, contractVersion="9.9")
    with pytest.raises(ErrorDeSobre):
        volcar_documento(documento)


def test_un_tipo_de_documento_desconocido_se_rechaza() -> None:
    """D14: nunca un nombre suelto y ambiguo como `reconstruction`."""
    documento = dict(MANIFEST_CUBE_V1, documentType="reconstruction")
    with pytest.raises(ErrorDeSobre):
        volcar_documento(documento)


def test_el_manifest_real_pasa_el_sobre_y_se_serializa() -> None:
    texto = volcar_documento(dict(MANIFEST_CUBE_V1, **sobre_de(PAQUETE_DE_RECONSTRUCCION)))
    assert json.loads(texto)["packageId"] == "cube-v1"


def test_el_sobre_no_tapa_la_comprobacion_de_no_finitos() -> None:
    """A1 sigue mandando: el sobre no es una puerta de atras."""
    from videomesh.contracts.serialization import ErrorNumeroNoFinito

    documento = dict(MANIFEST_CUBE_V1, **sobre_de(PAQUETE_DE_RECONSTRUCCION))
    documento["scale"] = {"status": "RELATIVE", "source": "NONE", "diagonal": float("inf")}
    with pytest.raises(ErrorNumeroNoFinito):
        volcar_documento(documento)
