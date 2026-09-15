"""La verificación se ejecuta sola, y dice qué falta cuando no puede.

Este repositorio no tiene remoto, asi que un workflow de CI seria un fichero que
**parece** una puerta y no se ejecuta nunca — el mismo fallo que el encargo 02
existe para cerrar, un nivel mas arriba. La puerta que si corre hoy es un hook de
git, y vive en el repositorio para que no dependa de como tenga configurada su
maquina cada uno.

Y una segunda cosa que no es de estilo: doce de los diecinueve ficheros de prueba
leen `../Dron/softsight`. Sin el vecino, un clon no falla con un mensaje: falla con
doce, y ninguno dice que lo que falta es un repositorio.
"""

import pathlib
import subprocess

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
HOOK = RAIZ / "scripts" / "hooks" / "pre-commit"
INSTALADO = RAIZ / ".git" / "hooks" / "pre-commit"
INSTALADOR = RAIZ / "scripts" / "instalar_hooks.sh"
VERIFY = RAIZ / "scripts" / "verify.sh"


def test_el_hook_vive_en_el_repositorio() -> None:
    """En `.git/hooks` no se versiona nada: ahi solo hay una copia de una maquina."""
    assert HOOK.is_file()
    assert HOOK.stat().st_mode & 0o111, "el hook tiene que ser ejecutable"


def test_el_hook_corre_la_verificacion_entera() -> None:
    """No un subconjunto rapido: la puerta es la misma que se pasa a mano."""
    assert "verify.sh" in HOOK.read_text(encoding="utf-8")


def test_el_instalador_existe_y_es_ejecutable() -> None:
    assert INSTALADOR.is_file()
    assert INSTALADOR.stat().st_mode & 0o111


def test_el_hook_instalado_es_el_del_repositorio() -> None:
    """Si divergen, la puerta de esta maquina ya no es la que el repositorio declara.

    Se instala con `bash scripts/instalar_hooks.sh`.
    """
    if not INSTALADO.exists():
        pytest.skip("hook sin instalar; se instala con scripts/instalar_hooks.sh")
    assert INSTALADO.read_text(encoding="utf-8") == HOOK.read_text(encoding="utf-8")


def test_el_hook_para_el_commit_cuando_la_verificacion_falla(tmp_path: pathlib.Path) -> None:
    """La comprobacion que decide si esto es una puerta o un adorno."""
    falso = tmp_path / "verify-que-falla.sh"
    falso.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="ascii")
    falso.chmod(0o755)
    guion = HOOK.read_text(encoding="utf-8").replace("scripts/verify.sh", str(falso))
    copia = tmp_path / "pre-commit"
    copia.write_text(guion, encoding="utf-8")
    copia.chmod(0o755)
    salida = subprocess.run(["bash", str(copia)], capture_output=True, text=True, cwd=RAIZ)
    assert salida.returncode != 0
    assert "verify" in (salida.stdout + salida.stderr).lower()


def test_la_verificacion_dice_que_falta_softsight_en_vez_de_reventar() -> None:
    """Doce ficheros de errores no le dicen a nadie que falta un repositorio."""
    texto = VERIFY.read_text(encoding="utf-8")
    assert "Dron/softsight" in texto


def test_la_verificacion_falla_pronto_si_no_esta_el_vecino(tmp_path: pathlib.Path) -> None:
    guion = VERIFY.read_text(encoding="utf-8").replace(
        "../Dron/softsight", str(tmp_path / "no-existe")
    )
    copia = tmp_path / "verify.sh"
    copia.write_text(guion, encoding="utf-8")
    copia.chmod(0o755)
    salida = subprocess.run(["bash", str(copia)], capture_output=True, text=True, cwd=RAIZ)
    assert salida.returncode != 0
    mensaje = (salida.stdout + salida.stderr).lower()
    assert "softsight" in mensaje
    assert "repositorio vecino" in mensaje
    # Y pronto: sin llegar a las pruebas, que es donde reventaria sin decir nada.
    # Se mira la cabecera que imprime verify.sh y no la palabra suelta: la ruta
    # temporal de pytest lleva «pytest» dentro, y eso hacia pasar la comprobacion
    # por el motivo equivocado.
    assert "== ruff ==" not in mensaje
    assert "== pytest ==" not in mensaje
