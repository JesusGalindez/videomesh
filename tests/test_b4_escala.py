"""B4 — D9: un presupuesto en unidades absolutas sobre una escala que no lo es se rechaza.

Los tres campos —`status`, `source` e incertidumbre— ya viajaban desde R0-A. **Lo
que faltaba era que rechazaran algo**: sin un sitio donde declarar un presupuesto,
la regla no tenia qué rechazar y la contradiccion que la decision ataja —metros
sobre una escala que nadie ha fijado— se colaba entera.

Las tres filas son del contrato, con sus identificadores:

    ABSOLUTE + scale.status != ABSOLUTE     SS-RECON-001
    ABSOLUTE sin unidad                     SS-RECON-002
    RELATIVE_TO_DIAGONAL con unidad         SS-RECON-002

R0 solo comprueba que el presupuesto sea **coherente con la escala**; evaluarlo
contra lo medido es R9. Decirlo asi evita leer un paquete aceptado como un paquete
aprobado.
"""

import json

import pytest

from videomesh.contracts.generacion import ESQUEMAS
from videomesh.domain.scale import ErrorDeEscala, comprobar_escala

MANIFEST = json.loads(
    (ESQUEMAS.parent / "artifacts" / "cube-v1" / "manifest.json").read_text(encoding="utf-8")
)

RELATIVA = {"status": "RELATIVE", "source": "NONE"}
ABSOLUTA = {
    "status": "ABSOLUTE",
    "source": "KNOWN_DISTANCE",
    "uncertainty": {"model": "GAUSSIAN", "value": 0.002},
}
DESVIACION = {"name": "desviacion", "units": "ABSOLUTE", "unit": "m", "max": 0.5}
FRACCION = {"name": "desviacion", "units": "RELATIVE_TO_DIAGONAL", "max": 0.01}


def test_cube_v1_pasa() -> None:
    """Escala RELATIVE y sin presupuestos: no hay nada que contradecir."""
    comprobar_escala(MANIFEST["scale"], MANIFEST.get("budgets", []))


def test_un_presupuesto_absoluto_sobre_escala_relativa_se_rechaza() -> None:
    """El caso que cierra B4. Medio metro sobre algo sin escala no significa nada."""
    with pytest.raises(ErrorDeEscala, match="SS-RECON-001"):
        comprobar_escala(RELATIVA, [DESVIACION])


def test_el_mensaje_trae_el_numero_la_unidad_y_el_estado() -> None:
    """Sin los tres, el productor no sabe si arreglar la escala o el presupuesto."""
    with pytest.raises(ErrorDeEscala) as capturado:
        comprobar_escala(RELATIVA, [DESVIACION])
    mensaje = str(capturado.value)
    assert "0.5" in mensaje
    assert "m" in mensaje
    assert "RELATIVE" in mensaje


def test_un_presupuesto_absoluto_sobre_escala_desconocida_tambien_se_rechaza() -> None:
    with pytest.raises(ErrorDeEscala, match="SS-RECON-001"):
        comprobar_escala({"status": "UNKNOWN", "source": "NONE"}, [DESVIACION])


def test_un_presupuesto_absoluto_sobre_escala_absoluta_pasa() -> None:
    """Lo que separa una regla de un rechazo indiscriminado."""
    comprobar_escala(ABSOLUTA, [DESVIACION])


def test_un_presupuesto_absoluto_sin_unidad_se_rechaza() -> None:
    sin_unidad = {k: v for k, v in DESVIACION.items() if k != "unit"}
    with pytest.raises(ErrorDeEscala, match="SS-RECON-002"):
        comprobar_escala(ABSOLUTA, [sin_unidad])


def test_una_fraccion_de_diagonal_con_unidad_se_rechaza() -> None:
    """No es simetria decorativa: una fraccion de diagonal no tiene unidad.

    Ponersela es declarar una escala por la puerta de atras — el consumidor leeria
    «0,01 m» donde el productor quiso decir «el 1 % de la pieza».
    """
    with pytest.raises(ErrorDeEscala, match="SS-RECON-002"):
        comprobar_escala(RELATIVA, [dict(FRACCION, unit="m")])


def test_una_fraccion_de_diagonal_sin_unidad_pasa_sobre_escala_relativa() -> None:
    """Es el fallback de D9: sin escala fijada, se presupuesta contra la diagonal."""
    comprobar_escala(RELATIVA, [FRACCION])


def test_dos_presupuestos_con_el_mismo_nombre_se_rechazan() -> None:
    """El esquema dice que el nombre identifica, asi que es unico."""
    with pytest.raises(ErrorDeEscala, match="desviacion"):
        comprobar_escala(ABSOLUTA, [DESVIACION, dict(DESVIACION, max=0.9)])


def test_un_nombre_fuera_del_vocabulario_se_trata_como_si_llevara_escala() -> None:
    """Se intento al reves y salio mal: suponer que no la lleva es suponer a favor.

    El vocabulario de magnitudes es de R9 y aqui no existe todavia, asi que **todo**
    nombre cuenta como con escala. Es el lado conservador, que es el que el
    contrato ya eligio.
    """
    raro = {"name": "loQueSea", "units": "ABSOLUTE", "unit": "mm", "max": 3}
    with pytest.raises(ErrorDeEscala, match="SS-RECON-001"):
        comprobar_escala(RELATIVA, [raro])
