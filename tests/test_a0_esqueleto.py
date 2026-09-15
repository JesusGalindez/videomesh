"""A0 — el repositorio existe como proyecto Python instalable.

La línea base del encargo: sin esto no cuelga nada de lo demás.
"""

import importlib


def test_el_paquete_videomesh_es_importable() -> None:
    modulo = importlib.import_module("videomesh")
    assert modulo.__version__


def test_la_version_del_contrato_no_vive_en_el_paquete() -> None:
    """D12: el consumidor comprueba el bloque, no un campo.

    Estuvo aqui como constante suelta hasta que el encargo 02 la saco: era una
    segunda fuente del mismo numero, correcta por casualidad. Hoy se lee de
    `contracts/estado.json`, que declara la combinacion entera.
    """
    import videomesh
    from videomesh.contracts.estado import version_del_paquete

    assert not hasattr(videomesh, "CONTRACT_VERSION")
    assert version_del_paquete() == "0.1"
