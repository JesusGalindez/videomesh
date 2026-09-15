"""`AGENTS.md` no se queda corto porque la lista se genera — y `--check` la vigila.

Un `AGENTS.md` escrito entero a mano miente tres commits despues: alguien anade
una prueba, no la apunta, y el agente frio que llega el mes siguiente ejecuta una
lista incompleta creyendola completa.

Lo que un script puede saber se genera; lo que no —donde va un cambio, que se
rompe si lo tocas— se escribe a mano y vive fuera de los delimitadores. Fingir que
un script sabe eso es peor que no tener el fichero.
"""

import pathlib

import pytest

from videomesh.contracts.agentes import (
    ErrorDeBloque,
    agents_md_generado,
    reemplazar_bloque,
)

RAIZ = pathlib.Path(__file__).resolve().parents[1]
AGENTS = RAIZ / "AGENTS.md"
TECHO = 150


def test_lo_commiteado_es_lo_que_sale_del_repositorio_de_hoy() -> None:
    """Si se anade una prueba y no se regenera, esto se pone rojo."""
    assert AGENTS.read_text(encoding="utf-8") == agents_md_generado()


def test_un_bloque_desactualizado_se_reescribe() -> None:
    """El caso que hace que la prueba valga: se ejerce sin tocar AGENTS.md."""
    viejo = "antes\n<!-- generado: puertas -->\nlista vieja\n<!-- /generado: puertas -->\ndespues"
    nuevo = reemplazar_bloque(viejo, "puertas", "lista nueva")
    assert "lista vieja" not in nuevo
    assert "lista nueva" in nuevo


def test_lo_escrito_a_mano_sobrevive_a_la_regeneracion() -> None:
    """Si el generador pisara lo de fuera, nadie volveria a escribir ahi nada."""
    viejo = (
        "A MANO ARRIBA\n<!-- generado: puertas -->\nx\n<!-- /generado: puertas -->\nA MANO ABAJO"
    )
    nuevo = reemplazar_bloque(viejo, "puertas", "y")
    assert nuevo.startswith("A MANO ARRIBA")
    assert nuevo.endswith("A MANO ABAJO")


def test_un_fichero_sin_los_delimitadores_se_rechaza() -> None:
    """Borrar el bloque no puede ser la forma de pasar la puerta."""
    with pytest.raises(ErrorDeBloque, match="puertas"):
        reemplazar_bloque("un AGENTS.md sin bloques", "puertas", "lo que sea")


def test_un_bloque_a_medio_cerrar_se_rechaza() -> None:
    with pytest.raises(ErrorDeBloque):
        reemplazar_bloque("<!-- generado: puertas -->\nsin cerrar", "puertas", "x")


def test_el_fichero_cabe_en_el_techo() -> None:
    """Corto a proposito: un AGENTS.md de trescientas lineas no lo lee nadie entero."""
    lineas = AGENTS.read_text(encoding="utf-8").count("\n") + 1
    assert lineas <= TECHO, f"AGENTS.md tiene {lineas} lineas y el techo son {TECHO}"


def test_la_lista_generada_nombra_todas_las_pruebas_del_repositorio() -> None:
    """Lo que hace que no se quede corta: sale del disco, no de que alguien apunte."""
    generado = agents_md_generado()
    for fichero in sorted((RAIZ / "tests").glob("test_*.py")):
        assert fichero.name in generado
