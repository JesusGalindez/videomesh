"""Core Foundation, segunda pieza — stages, determinismo y resume.

§11: cada stage mantiene **su propia verdad de ejecución**, y registra lo que hizo
—artifacts, hashes de entrada y de salida, duración, proveedor y su versión—.

Lo que decide si un stage se puede saltar no es su estado: son los **hashes de
entrada**. Un stage COMPLETE cuya entrada cambió no está hecho, está caducado, y
saltárselo produce una salida que describe otra cosa.

Y §11 otra vez, sobre publicar: un stage que publica paquete no es COMPLETE hasta
que el rename atómico salió bien. Declararlo antes deja un COMPLETE sobre un
paquete que no existe.
"""

import pathlib

import pytest

from videomesh.domain.errores import ErrorDeProyecto
from videomesh.domain.stage import (
    Determinismo,
    EjecucionDeStage,
    EstadoDeStage,
    hay_que_reejecutar,
)
from videomesh.project.stages import historial_de, registrar_stage


def _ejecucion(**cambios: object) -> EjecucionDeStage:
    base = {
        "stage": "S03",
        "estado": EstadoDeStage.COMPLETE,
        "hash_de_entrada": "aa" * 32,
        "hash_de_salida": "bb" * 32,
        "determinismo": Determinismo.DETERMINISTA,
        "proveedor": "videomesh",
        "version_del_proveedor": "0.1.0",
        "duracion_s": 1.5,
    }
    base.update(cambios)
    return EjecucionDeStage(**base)  # type: ignore[arg-type]


def test_los_seis_estados_de_stage() -> None:
    assert [e.value for e in EstadoDeStage] == [
        "PENDING",
        "RUNNING",
        "COMPLETE",
        "FAILED",
        "SKIPPED",
        "CACHED",
    ]


def test_los_cuatro_determinismos() -> None:
    """§11: no confundirlo con MeasurementClass ni ReproducibilityMode, que son de métricas."""
    assert [d.value for d in Determinismo] == [
        "DETERMINISTIC",
        "DETERMINISTIC_WITH_SEED",
        "BEST_EFFORT",
        "NON_DETERMINISTIC_PROVIDER",
    ]


def test_un_stage_completo_con_la_misma_entrada_no_se_reejecuta() -> None:
    assert not hay_que_reejecutar(_ejecucion(), hash_de_entrada="aa" * 32)


def test_un_stage_completo_cuya_entrada_cambio_si_se_reejecuta() -> None:
    """Lo que decide es el hash de entrada, no el estado. COMPLETE no es «vigente»."""
    assert hay_que_reejecutar(_ejecucion(), hash_de_entrada="cc" * 32)


@pytest.mark.parametrize(
    "estado", [EstadoDeStage.PENDING, EstadoDeStage.RUNNING, EstadoDeStage.FAILED]
)
def test_un_stage_que_no_acabo_se_reejecuta_aunque_la_entrada_sea_la_misma(
    estado: EstadoDeStage,
) -> None:
    """RUNNING es el caso que importa: un proceso muerto deja el stage ahi para siempre."""
    assert hay_que_reejecutar(_ejecucion(estado=estado), hash_de_entrada="aa" * 32)


def test_un_stage_cacheado_cuenta_como_hecho() -> None:
    assert not hay_que_reejecutar(
        _ejecucion(estado=EstadoDeStage.CACHED), hash_de_entrada="aa" * 32
    )


def test_sin_ejecucion_previa_hay_que_ejecutar() -> None:
    assert hay_que_reejecutar(None, hash_de_entrada="aa" * 32)


def test_un_stage_no_determinista_no_se_puede_reutilizar() -> None:
    """Reutilizar una salida que no se puede reproducir es afirmar algo que no se sabe.

    El estado dice que salió bien; el determinismo dice si volvería a salir igual, y
    solo lo segundo justifica saltarse el trabajo.
    """
    no_reproducible = _ejecucion(determinismo=Determinismo.NO_DETERMINISTA)
    assert hay_que_reejecutar(no_reproducible, hash_de_entrada="aa" * 32)


def test_un_stage_con_semilla_si_se_reutiliza_si_la_semilla_es_la_misma() -> None:
    con_semilla = _ejecucion(determinismo=Determinismo.DETERMINISTA_CON_SEMILLA, semilla=7)
    assert not hay_que_reejecutar(con_semilla, hash_de_entrada="aa" * 32, semilla=7)
    assert hay_que_reejecutar(con_semilla, hash_de_entrada="aa" * 32, semilla=8)


def test_un_stage_completo_sin_hash_de_salida_se_rechaza() -> None:
    """Un COMPLETE que no dice qué produjo no se puede comprobar ni reutilizar."""
    with pytest.raises(ValueError, match="hash_de_salida"):
        _ejecucion(hash_de_salida=None)


def test_un_stage_fallido_no_necesita_hash_de_salida() -> None:
    _ejecucion(estado=EstadoDeStage.FAILED, hash_de_salida=None)


def test_una_duracion_negativa_se_rechaza() -> None:
    with pytest.raises(ValueError, match="duracion"):
        _ejecucion(duracion_s=-1.0)


# --- el historial en disco --------------------------------------------------


def test_el_historial_se_guarda_y_se_relee(tmp_path: pathlib.Path) -> None:
    from videomesh.project.store import crear_proyecto

    crear_proyecto(tmp_path / "p", nombre="p")
    registrar_stage(tmp_path / "p", _ejecucion())
    (guardada,) = historial_de(tmp_path / "p")
    assert guardada == _ejecucion()


def test_la_ultima_ejecucion_de_un_stage_es_la_que_manda(tmp_path: pathlib.Path) -> None:
    from videomesh.project.store import crear_proyecto

    crear_proyecto(tmp_path / "p", nombre="p")
    registrar_stage(tmp_path / "p", _ejecucion(estado=EstadoDeStage.FAILED, hash_de_salida=None))
    registrar_stage(tmp_path / "p", _ejecucion())
    assert historial_de(tmp_path / "p")[-1].estado is EstadoDeStage.COMPLETE


def test_el_historial_no_pierde_lo_que_fallo(tmp_path: pathlib.Path) -> None:
    """Borrar el intento fallido es borrar la unica pista de por que se reejecuto."""
    from videomesh.project.store import crear_proyecto

    crear_proyecto(tmp_path / "p", nombre="p")
    registrar_stage(tmp_path / "p", _ejecucion(estado=EstadoDeStage.FAILED, hash_de_salida=None))
    registrar_stage(tmp_path / "p", _ejecucion())
    assert len(historial_de(tmp_path / "p")) == 2


def test_registrar_sobre_algo_que_no_es_proyecto_se_rechaza(tmp_path: pathlib.Path) -> None:
    with pytest.raises(ErrorDeProyecto):
        registrar_stage(tmp_path, _ejecucion())
