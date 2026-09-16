"""El pipeline por la CLI — §20 del roadmap.

De los cuatro stages, **hoy solo uno puede hacer su trabajo**: `produce`, que
fabrica el paquete y lo sella. Los otros tres necesitan FFmpeg o COLMAP, y en
esta máquina no están.

Que no puedan correr no significa que no deban existir. Un comando ausente le
dice al usuario que se equivocó de nombre; uno que falla con
`ProveedorNoDisponible` le dice qué falta, para qué hace falta y cómo se
instala. Es la regla de §21 —una incompatibilidad conocida falla pronto— movida
al punto de uso.

Lo que sí se comprueba entero es la única cosa que importa de `produce`: que el
paquete que escribe **lo certifica el consumidor real de SoftSight**.
"""

import json
import pathlib
import shutil
import subprocess
from typing import Any

import pytest

from videomesh.application.pipeline import STAGES, ejecutar_stage, hash_de_entrada
from videomesh.contracts.generacion import ESQUEMAS
from videomesh.domain.errores import ProveedorNoDisponible
from videomesh.domain.project import Preparacion, preparacion_de
from videomesh.domain.stage import EstadoDeStage
from videomesh.project.stages import ultima_de
from videomesh.project.store import abrir_proyecto, crear_proyecto

CONSUMIDOR = ESQUEMAS.parent / "tools" / "reconstruction.mjs"


@pytest.fixture
def proyecto(tmp_path: pathlib.Path) -> pathlib.Path:
    ruta = tmp_path / "proyecto"
    crear_proyecto(ruta, nombre="prueba")
    return ruta


# --- produce, que es el que hoy trabaja -------------------------------------


def test_produce_escribe_un_paquete_sellado(proyecto: pathlib.Path) -> None:
    manifest = ejecutar_stage(proyecto, "produce")
    assert manifest.is_file()
    documento = json.loads(manifest.read_text(encoding="utf-8"))
    assert documento["state"] == "SEALED"


def test_produce_deja_la_ejecucion_registrada(proyecto: pathlib.Path) -> None:
    """Un stage que no registra lo que hizo no se puede reanudar ni comprobar."""
    ejecutar_stage(proyecto, "produce")
    ultima = ultima_de(proyecto, "produce")
    assert ultima is not None
    assert ultima.estado is EstadoDeStage.COMPLETE
    assert ultima.hash_de_salida


def test_produce_dos_veces_no_rehace_el_trabajo(proyecto: pathlib.Path) -> None:
    """§11: lo que decide saltárselo no es el estado, son los hashes. La entrada
    no cambió y el stage es determinista, así que la segunda vez es CACHED."""
    primero = ejecutar_stage(proyecto, "produce")
    segundo = ejecutar_stage(proyecto, "produce")
    assert segundo == primero
    ultima = ultima_de(proyecto, "produce")
    assert ultima is not None
    assert ultima.estado is EstadoDeStage.CACHED


def test_produce_actualiza_lo_que_el_proyecto_tiene(proyecto: pathlib.Path) -> None:
    """La preparación se deriva de los artifacts, nunca se declara (§8)."""
    assert preparacion_de(abrir_proyecto(proyecto)) == ()
    ejecutar_stage(proyecto, "produce")
    assert Preparacion.RECONSTRUCCION in preparacion_de(abrir_proyecto(proyecto))


@pytest.mark.skipif(
    shutil.which("node") is None or not CONSUMIDOR.exists(),
    reason="hace falta node y el consumidor de SoftSight",
)
def test_el_paquete_de_produce_lo_certifica_softsight(proyecto: pathlib.Path) -> None:
    """La única comprobación que vale: el consumidor real, no mi opinión de él."""
    manifest = ejecutar_stage(proyecto, "produce")
    salida = subprocess.run(
        ["node", str(CONSUMIDOR), "inspect", str(manifest)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert salida.returncode == 0, salida.stderr[-2000:]
    informe: dict[str, Any] = json.loads(salida.stdout)
    assert informe["execution"] == "COMPLETE"
    assert informe["certification"] == "PASS"


# --- los tres que hoy no pueden ---------------------------------------------


@pytest.mark.parametrize("stage", ["analyze", "build", "reconstruct"])
def test_los_stages_con_binario_ausente_fallan_tipado(proyecto: pathlib.Path, stage: str) -> None:
    """No un `FileNotFoundError` de subprocess treinta marcos más abajo."""
    with pytest.raises(ProveedorNoDisponible):
        ejecutar_stage(proyecto, stage)


@pytest.mark.parametrize("stage", ["analyze", "build", "reconstruct"])
def test_el_fallo_dice_que_falta_para_que_y_como_se_instala(
    proyecto: pathlib.Path, stage: str
) -> None:
    """Lo que distingue un diagnóstico de un mensaje de error."""
    with pytest.raises(ProveedorNoDisponible) as fallo:
        ejecutar_stage(proyecto, stage)
    texto = str(fallo.value)
    assert "brew install" in texto
    assert any(binario in texto for binario in ("ffmpeg", "colmap"))


def test_un_stage_que_no_existe_se_rechaza_y_dice_cuales_hay(
    proyecto: pathlib.Path,
) -> None:
    with pytest.raises(ValueError) as fallo:
        ejecutar_stage(proyecto, "reconstruir-el-universo")
    assert all(nombre in str(fallo.value) for nombre in STAGES)


def test_los_cuatro_stages_van_en_el_orden_del_pipeline() -> None:
    """El orden importa: `produce` no puede ir antes que `reconstruct`."""
    assert STAGES == ("analyze", "build", "reconstruct", "produce")


def test_dos_proyectos_distintos_producen_el_mismo_paquete(tmp_path: pathlib.Path) -> None:
    """La afirmación `DETERMINISTA` del registro, comprobada en vez de supuesta.

    Si esto no se cumpliera, `CACHED` estaría reutilizando una salida que no se
    puede reproducir, que es justo lo que §11 prohíbe saltarse.
    """
    manifiestos = []
    for nombre in ("uno", "otro"):
        ruta = tmp_path / nombre
        crear_proyecto(ruta, nombre=nombre)
        manifiestos.append(ejecutar_stage(ruta, "produce"))

    primero, segundo = (json.loads(m.read_text(encoding="utf-8")) for m in manifiestos)
    assert primero["packageId"] == segundo["packageId"]


def test_el_hash_de_entrada_no_lo_mueve_lo_que_el_propio_stage_escribe(
    proyecto: pathlib.Path,
) -> None:
    """La versión anterior hasheaba `project.json`, que `produce` reescribe al
    acabar: el stage se invalidaba a si mismo y nunca podia dar CACHED."""
    antes = hash_de_entrada(proyecto)
    ejecutar_stage(proyecto, "produce")
    assert hash_de_entrada(proyecto) == antes
