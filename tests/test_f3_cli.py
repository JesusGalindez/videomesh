"""Core Foundation, tercera pieza — la CLI.

§20 y §21. Cuatro órdenes, y `doctor` es la que más trabaja: reporta **existencia
y compatibilidad**, no solo si un binario está. Un COLMAP instalado que escribe un
formato que no leemos es tan inútil como uno ausente, y la diferencia solo se ve
comprobándolo.

La regla de §21: una incompatibilidad contractual conocida **falla pronto**, antes
de las etapas caras. Descubrirla después de una reconstrucción de dos horas es
descubrirla tarde.
"""

import json
import pathlib
import shutil

import pytest

from videomesh.cli.app import main


def _correr(*argumentos: str) -> tuple[int, str]:
    from contextlib import redirect_stdout
    from io import StringIO

    salida = StringIO()
    with redirect_stdout(salida):
        codigo = main(list(argumentos))
    return codigo, salida.getvalue()


def test_sin_argumentos_dice_que_hay() -> None:
    codigo, texto = _correr()
    assert codigo != 0
    for orden in ("init", "status", "doctor", "resume"):
        assert orden in texto


def test_la_ayuda_sale_con_cero() -> None:
    codigo, texto = _correr("--help")
    assert codigo == 0
    assert "videomesh" in texto


def test_una_orden_que_no_existe_lo_dice_y_no_revienta() -> None:
    codigo, texto = _correr("reconstruir-el-universo")
    assert codigo != 0
    assert "reconstruir-el-universo" in texto


# --- init ------------------------------------------------------------------


def test_init_crea_el_proyecto(tmp_path: pathlib.Path) -> None:
    codigo, texto = _correr("init", str(tmp_path / "torreta"))
    assert codigo == 0
    assert (tmp_path / "torreta" / "project.json").is_file()
    assert "torreta" in texto


def test_init_sobre_un_proyecto_existente_falla_sin_pisarlo(tmp_path: pathlib.Path) -> None:
    _correr("init", str(tmp_path / "torreta"))
    antes = (tmp_path / "torreta" / "project.json").read_bytes()
    codigo, texto = _correr("init", str(tmp_path / "torreta"))
    assert codigo != 0
    assert "ya existe" in texto
    assert (tmp_path / "torreta" / "project.json").read_bytes() == antes


# --- status ----------------------------------------------------------------


def test_status_dice_el_estado_y_para_que_esta_preparado(tmp_path: pathlib.Path) -> None:
    _correr("init", str(tmp_path / "torreta"))
    codigo, texto = _correr("status", str(tmp_path / "torreta"))
    assert codigo == 0
    assert "CREADO" in texto
    assert "preparado" in texto.lower()


def test_status_sobre_algo_que_no_es_proyecto_falla_con_mensaje(tmp_path: pathlib.Path) -> None:
    codigo, texto = _correr("status", str(tmp_path))
    assert codigo != 0
    assert "project.json" in texto


def test_status_no_revienta_con_un_proyecto_sin_historial(tmp_path: pathlib.Path) -> None:
    _correr("init", str(tmp_path / "torreta"))
    codigo, _ = _correr("status", str(tmp_path / "torreta"))
    assert codigo == 0


# --- doctor ----------------------------------------------------------------


def test_doctor_reporta_existencia_y_compatibilidad() -> None:
    """§21: existencia **y** compatibilidad. Un binario presente puede no servir."""
    codigo, texto = _correr("doctor")
    assert "SoftSight" in texto
    assert "esquema" in texto.lower()
    del codigo


def test_doctor_dice_que_falta_colmap_y_ffmpeg_sin_fallar_por_ello() -> None:
    """No están instalados, y R0 no los necesita: decirlo no es lo mismo que fallar."""
    _, texto = _correr("doctor")
    assert "COLMAP" in texto
    assert "FFmpeg" in texto


def test_doctor_comprueba_el_hash_del_esquema_contra_el_registro() -> None:
    """La incompatibilidad contractual se ve aquí, antes de las etapas caras."""
    _, texto = _correr("doctor")
    assert "COINCIDE" in texto.upper()


def test_doctor_sale_cero_cuando_lo_que_hace_falta_para_R0_esta() -> None:
    """Lo que falta para etapas futuras se reporta; no convierte hoy en rojo."""
    codigo, _ = _correr("doctor")
    assert codigo == 0


def test_doctor_en_json_es_legible_por_una_maquina() -> None:
    """Para que una puerta pueda leerlo sin parsear un informe humano."""
    codigo, texto = _correr("doctor", "--json")
    assert codigo == 0
    informe = json.loads(texto)
    assert informe["documentType"] == "videomesh.doctor"
    assert isinstance(informe["comprobaciones"], list)


# --- resume ----------------------------------------------------------------


def test_resume_dice_que_stages_habria_que_reejecutar(tmp_path: pathlib.Path) -> None:
    from videomesh.domain.stage import Determinismo, EjecucionDeStage, EstadoDeStage
    from videomesh.project.stages import registrar_stage

    _correr("init", str(tmp_path / "torreta"))
    registrar_stage(
        tmp_path / "torreta",
        EjecucionDeStage(
            stage="S03",
            estado=EstadoDeStage.COMPLETE,
            hash_de_entrada="aa" * 32,
            hash_de_salida="bb" * 32,
            determinismo=Determinismo.DETERMINISTA,
            proveedor="videomesh",
            version_del_proveedor="0.1.0",
            duracion_s=1.0,
        ),
    )
    codigo, texto = _correr("resume", str(tmp_path / "torreta"))
    assert codigo == 0
    assert "S03" in texto


def test_resume_sobre_un_proyecto_sin_historial_lo_dice(tmp_path: pathlib.Path) -> None:
    _correr("init", str(tmp_path / "torreta"))
    codigo, texto = _correr("resume", str(tmp_path / "torreta"))
    assert codigo == 0
    assert "nada" in texto.lower() or "sin" in texto.lower()


# --- la regla de dependencia ------------------------------------------------


def test_el_dominio_no_importa_nada_de_fuera() -> None:
    """§6: domain no importa providers, ni la CLI, ni adapters. Nunca al reves.

    Se vigila por ausencia porque un import de mas no rompe nada el dia que se
    escribe: rompe el dia que alguien quiere usar el dominio sin el resto.
    """
    dominio = pathlib.Path(__file__).resolve().parents[1] / "src" / "videomesh" / "domain"
    prohibidos = ("videomesh.providers", "videomesh.adapters", "videomesh.cli", "videomesh.project")
    for ruta in dominio.rglob("*.py"):
        texto = ruta.read_text(encoding="utf-8")
        for prohibido in prohibidos:
            assert f"import {prohibido}" not in texto, f"{ruta.name} importa {prohibido}"
            assert f"from {prohibido}" not in texto, f"{ruta.name} importa de {prohibido}"


# --- pipeline ---------------------------------------------------------------


def test_produce_por_la_cli_escribe_el_paquete_y_dice_donde(tmp_path: pathlib.Path) -> None:
    ruta = tmp_path / "proyecto"
    assert _correr("init", str(ruta))[0] == 0
    codigo, texto = _correr("produce", str(ruta))
    assert codigo == 0
    assert "manifest.json" in texto


def test_analyze_sin_ffmpeg_sale_uno_y_dice_como_instalarlo(tmp_path: pathlib.Path) -> None:
    """El comando existe a proposito: uno ausente solo dice «no existe esa orden»."""
    ruta = tmp_path / "proyecto"
    _correr("init", str(ruta))
    codigo, texto = _correr("analyze", str(ruta))
    assert codigo == 1
    assert "ffmpeg" in texto
    assert "brew install" in texto


def test_validate_pasa_el_paquete_por_el_consumidor_de_verdad(tmp_path: pathlib.Path) -> None:
    """D1: se le pasa la ruta del manifest, nunca base64 ni el contenido."""
    if shutil.which("node") is None:
        pytest.skip("hace falta node")
    ruta = tmp_path / "proyecto"
    _correr("init", str(ruta))
    _correr("produce", str(ruta))
    codigo, texto = _correr("validate", str(ruta))
    assert codigo == 0, texto
    assert "COMPLETE" in texto
    assert "PASS" in texto


def test_validate_sin_paquete_lo_dice_en_vez_de_reventar(tmp_path: pathlib.Path) -> None:
    ruta = tmp_path / "proyecto"
    _correr("init", str(ruta))
    codigo, texto = _correr("validate", str(ruta))
    assert codigo == 1
    assert "produce" in texto


def test_la_ayuda_nombra_las_ordenes_del_pipeline() -> None:
    _, texto = _correr("--help")
    for orden in ("analyze", "build", "reconstruct", "produce", "validate"):
        assert orden in texto
