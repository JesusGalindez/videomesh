"""Encargo 04, C1 — la retopología, **declarada sin instrumento** y no sustituida.

Los dos proveedores que el encargo nombra —Instant Meshes y QuadriFlow— no están en
esta máquina y no se pueden poner: no están en PyPI y no hay brew ni cmake. El encargo
permite parar cuando falta el instrumento; lo que no permite es taparlo.

Y aquí taparlo sería fácil y peor que no hacer nada: lo único que el proveedor de
malla que ya está sabe hacer con quads conserva los vértices originales, así que no
alinearía con la forma, no decimaría y no tendría ninguna pérdida que publicar. Una
etapa de quads que no dice cuánto costó **parece** hecha, y es justo lo que este
proyecto existe para no producir.

Lo que se prueba, entonces, es que la ausencia se ve sin lanzar nada —en la cadena,
en `doctor` y en la orden— y que tiene las tres partes que pide el repositorio: qué
falta, para qué hace falta y cómo se consigue.
"""

import pathlib

import pytest

from videomesh.application.cadena import Paso, Situacion, estado_de_la_cadena
from videomesh.application.retopologia import (
    ETAPA,
    PROVEEDOR,
    exigir,
    instalado,
    motivo_de_ausencia,
)
from videomesh.cli.app import main
from videomesh.domain.errores import ProveedorNoDisponible
from videomesh.project.store import crear_proyecto

RAIZ = pathlib.Path(__file__).resolve().parents[1]


def _proyecto(tmp_path: pathlib.Path) -> pathlib.Path:
    ruta = tmp_path / "proyecto"
    crear_proyecto(ruta, nombre="prueba")
    return ruta


def _paso(proyecto: pathlib.Path) -> Paso:
    return next(paso for paso in estado_de_la_cadena(proyecto) if paso.etapa == ETAPA)


def test_la_cadena_dice_que_falta_el_instrumento_sin_lanzar_nada(
    tmp_path: pathlib.Path,
) -> None:
    """La ausencia es un estado de la cadena, no un fallo que se descubre al intentar.

    Un agente que lee `status` tiene que poder saber qué etapas puede hacer y cuáles no
    **antes** de ejecutarlas: si hay que lanzar la etapa para enterarse, el aviso llega
    cuando ya se ha gastado el tiempo.
    """
    paso = _paso(_proyecto(tmp_path))
    assert paso.situacion is Situacion.SIN_INSTRUMENTO
    assert PROVEEDOR in paso.motivo


def test_el_motivo_dice_que_no_se_sustituye(tmp_path: pathlib.Path) -> None:
    """Y con la razón, que es la parte que evita que el siguiente lo intente.

    El estado dice «no se puede»; el motivo dice «no se puede, y no por falta de
    ganas»: el proveedor que sí está da una etapa sin número.
    """
    paso = _paso(_proyecto(tmp_path))
    assert "no se sustituye" in paso.motivo
    assert "no alinea" in paso.motivo


def test_el_motivo_de_la_cadena_es_el_mismo_que_el_de_la_etapa() -> None:
    """Un texto y un sitio: `status` y la orden no pueden decir cosas distintas."""
    motivo = motivo_de_ausencia()
    if instalado():  # pragma: no cover - esta máquina no tiene ninguno de los dos
        assert motivo is None
        return
    assert motivo is not None
    # El texto del codigo va sin tildes, como el resto de los mensajes del repositorio.
    assert motivo.startswith("falta el proveedor de retopologia")


def test_exigir_dice_que_falta_para_que_y_como_se_instala() -> None:
    """Las tres partes del mensaje, que son las de `providers/externos.py`.

    Sin la segunda, quien no conozca la cadena no sabe si puede seguir sin ello; sin
    la tercera, tiene que ir a buscarlo fuera.
    """
    if instalado():  # pragma: no cover - esta máquina no tiene ninguno de los dos
        exigir()
        pytest.skip("el proveedor está instalado: el caso rojo no aplica")

    with pytest.raises(ProveedorNoDisponible) as fallo:
        exigir()
    mensaje = str(fallo.value)
    assert PROVEEDOR in mensaje  # qué falta
    assert "quads alineados" in mensaje  # para qué
    assert "fuente" in mensaje  # cómo se consigue
    assert "videomesh doctor" in mensaje  # y dónde está el resto del entorno


def test_la_orden_falla_diciendo_lo_mismo_y_no_hace_nada_mas(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`videomesh retopologia` existe y falla bien, como los tres stages del pipeline."""
    codigo = main(["retopologia", str(_proyecto(tmp_path))])
    salida = capsys.readouterr().out
    if instalado():  # pragma: no cover - esta máquina no tiene ninguno de los dos
        assert codigo == 1
        return
    assert codigo == 1
    assert PROVEEDOR in salida


def test_la_etapa_que_falta_no_toca_el_proveedor_de_malla() -> None:
    """La puerta que impide la sustitución cómoda, por lo de siempre: que no se pueda
    volver atrás sin que salte algo.

    El módulo que declara la ausencia **no importa** el proveedor que sí está. Si
    alguien llama a su filtro de quads desde aquí, esa importación aparece y esta
    prueba la nombra.
    """
    fuente = (RAIZ / "src" / "videomesh" / "application" / "retopologia.py").read_text(
        encoding="utf-8"
    )
    importes = [linea for linea in fuente.splitlines() if linea.startswith(("import ", "from "))]
    for proveedor in ("pymeshlab", "xatlas"):
        assert not any(proveedor in linea for linea in importes), (
            f"`retopologia.py` importa {proveedor}: sustituir el proveedor que falta por "
            "uno que da menos es lo único que este bloque no puede hacer"
        )
