"""A0 — el repositorio existe como proyecto Python instalable.

La línea base del encargo: sin esto no cuelga nada de lo demás.
"""

import importlib


def test_el_paquete_videomesh_es_importable() -> None:
    modulo = importlib.import_module("videomesh")
    assert modulo.__version__


def test_el_paquete_declara_su_version_de_contrato() -> None:
    """El contrato que hoy se habla con SoftSight es el 0.1 (D16)."""
    from videomesh import CONTRACT_VERSION

    assert CONTRACT_VERSION == "0.1"
