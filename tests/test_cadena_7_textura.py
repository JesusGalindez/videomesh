"""Encargo 04, D1 — la textura, **declarada sin instrumento** y no sustituida.

La etapa la pide el encargo con **OpenMVS `TextureMesh`**: proyecta los fotogramas
reales sobre la malla, y ese color —el desgaste, las manchas, la luz vista por la
cámara— no lo da ningún generador. El instrumento no está en esta máquina y no se
puede poner: no está en PyPI, y no hay brew ni cmake para construirlo (comprobado
el 2026-09-16). El encargo permite parar cuando falta el instrumento; lo que no
permite es taparlo.

Y aquí taparlo también sería fácil y peor que no hacer nada: los colores de la nube
dispersa ya están, y hornearlos sobre el atlas es lo que el proveedor de malla sabe
hacer. Pero lo que se interpola desde la nube **no es el color que vio ninguna
cámara**: es la luz de todas, barata de calcular y sin ninguna correspondencia
texel-fotograma que auditar. Una textura que nadie fotografió **parece** la etapa
D1 hecha, y es justo lo que este proyecto existe para no producir.

Lo que se prueba, entonces, es que la ausencia se ve sin lanzar nada —en la cadena,
en `doctor` y en la orden— y que tiene las tres partes que pide el repositorio: qué
falta, para qué hace falta y cómo se consigue.
"""

import pathlib

import pytest

from videomesh.application.cadena import Paso, Situacion, estado_de_la_cadena
from videomesh.application.textura import (
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

    El mismo criterio que cerró C1: `status` basta para saber qué etapas se pueden
    hacer hoy, sin gastar tiempo en la que no.
    """
    paso = _paso(_proyecto(tmp_path))
    assert paso.situacion is Situacion.SIN_INSTRUMENTO
    assert PROVEEDOR in paso.motivo


def test_el_motivo_dice_que_no_se_sustituye(tmp_path: pathlib.Path) -> None:
    """Y con la razón, que es la parte que evita que el siguiente lo intente.

    El estado dice «no se puede»; el motivo dice por qué el atajo que hay al lado
    no es la etapa: una textura horneada desde la nube no la vio ninguna cámara.
    """
    paso = _paso(_proyecto(tmp_path))
    assert "no se sustituye" in paso.motivo
    assert "ninguna cámara" in paso.motivo


def test_el_motivo_de_la_cadena_es_el_mismo_que_el_de_la_etapa() -> None:
    """Un texto y un sitio: `status` y la orden no pueden decir cosas distintas."""
    motivo = motivo_de_ausencia()
    if instalado():  # pragma: no cover - esta máquina no tiene TextureMesh
        assert motivo is None
        return
    assert motivo is not None
    # El texto del codigo va sin tildes, como el resto de los mensajes del repositorio.
    assert motivo.startswith("falta el proveedor de textura")


def test_exigir_dice_que_falta_para_que_y_como_se_instala() -> None:
    """Las tres partes del mensaje, que son las de `providers/externos.py`."""
    if instalado():  # pragma: no cover - esta máquina no tiene TextureMesh
        exigir()
        pytest.skip("el proveedor está instalado: el caso rojo no aplica")

    with pytest.raises(ProveedorNoDisponible) as fallo:
        exigir()
    mensaje = str(fallo.value)
    assert PROVEEDOR in mensaje  # qué falta
    assert "fotogramas" in mensaje  # para qué
    assert "fuente" in mensaje  # cómo se consigue
    assert "videomesh doctor" in mensaje  # y dónde está el resto del entorno


def test_la_orden_falla_diciendo_lo_mismo_y_no_hace_nada_mas(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`videomesh textura` existe y falla bien, como `retopologia`."""
    codigo = main(["textura", str(_proyecto(tmp_path))])
    salida = capsys.readouterr().out
    if instalado():  # pragma: no cover - esta máquina no tiene TextureMesh
        assert codigo == 1
        return
    assert codigo == 1
    assert PROVEEDOR in salida


def test_la_etapa_que_falta_no_importa_los_proveedores_que_estan() -> None:
    """La puerta que impide la sustitución cómoda, la misma que en C1.

    El módulo que declara la ausencia **no importa** el proveedor de malla: si
    alguien hornea colores desde aquí, esa importación aparece y esta prueba la
    nombra.
    """
    fuente = (RAIZ / "src" / "videomesh" / "application" / "textura.py").read_text(encoding="utf-8")
    importes = [linea for linea in fuente.splitlines() if linea.startswith(("import ", "from "))]
    for proveedor in ("pymeshlab", "xatlas"):
        assert not any(proveedor in linea for linea in importes), (
            f"`textura.py` importa {proveedor}: hornear colores de vertice no es proyectar "
            "fotogramas, y parece la etapa D1 hecha sin haberla hecho"
        )
