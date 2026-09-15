"""D2 — VideoMesh actúa por el identificador, nunca por el mensaje.

    code     SS-PKG-001         identificador neutro; esto es lo que se parsea
    reason   RUTA_FUERA_DE_LA_RAIZ   motivo canonico, vocabulario del contrato
    message  texto en español, con la ruta concreta; **nunca se parsea**

El motivo de la regla no es de estilo: el 2026-09-13 el idioma de los mensajes
cambió a español entero, los treinta y seis textos con él, y **eso no rompió a
nadie** precisamente porque lo que se parsea es el identificador.

Y un motivo puede repetirse mientras un identificador no: `SS-PKG-001` y
`SS-PKG-003` comparten `RUTA_FUERA_DE_LA_RAIZ` porque el resultado es el mismo y
la causa no. Quien agrupe por motivo pierde esa diferencia.
"""

import json
import pathlib
import shutil
import subprocess
from typing import Any

import pytest

from videomesh.application.cube_v1 import generar_cube_v1
from videomesh.contracts.codigos import (
    ESPACIOS,
    avisos_de,
    es_identificador,
    espacio_de,
    veredicto_de,
)
from videomesh.contracts.generacion import ESQUEMAS

CONSUMIDOR = ESQUEMAS.parent / "tools" / "reconstruction.mjs"

necesita_node = pytest.mark.skipif(
    shutil.which("node") is None or not CONSUMIDOR.exists(),
    reason="hace falta node y el consumidor de SoftSight",
)


@pytest.fixture(scope="module")
def informe(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    if shutil.which("node") is None or not CONSUMIDOR.exists():
        pytest.skip("hace falta node y el consumidor de SoftSight")
    paquete = generar_cube_v1(tmp_path_factory.mktemp("codigos") / "cube-v1")
    salida = subprocess.run(
        ["node", str(CONSUMIDOR), "inspect", str(paquete / "manifest.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    devuelto: dict[str, Any] = json.loads(salida.stdout)
    return devuelto


def test_los_doce_espacios_son_los_que_el_contrato_declara() -> None:
    assert ESPACIOS == (
        "SS-PKG",
        "SS-IO",
        "SS-GEO",
        "SS-RECON",
        "SS-CAM",
        "SS-COV",
        "SS-CONF",
        "SS-PROD",
        "SS-LOD",
        "SS-UV",
        "SS-PBR",
        "SS-COLL",
    )


@pytest.mark.parametrize("texto", ["SS-PKG-001", "SS-RECON-002", "SS-COV-001"])
def test_reconoce_un_identificador_bien_formado(texto: str) -> None:
    assert es_identificador(texto)


@pytest.mark.parametrize(
    "texto",
    [
        "SS-XXX-001",  # espacio que el contrato no declara
        "SS-PKG-1",  # sin los tres digitos
        "ss-pkg-001",  # minusculas
        "SS-PKG-001 la ruta sale de la raiz",  # el identificador con su mensaje pegado
        "la ruta sale de la raiz",  # solo el mensaje
        "",
    ],
)
def test_rechaza_lo_que_no_es_un_identificador(texto: str) -> None:
    assert not es_identificador(texto)


def test_el_espacio_sale_del_identificador() -> None:
    assert espacio_de("SS-RECON-002") == "SS-RECON"


@necesita_node
def test_lee_los_avisos_del_informe_real_por_su_identificador(informe: dict[str, Any]) -> None:
    """El cubo de VideoMesh produce uno: cuatro camaras no ven un cubo entero."""
    assert avisos_de(informe) == ["SS-COV-001"]


@necesita_node
def test_el_veredicto_son_dos_ejes_y_no_uno(informe: dict[str, Any]) -> None:
    """D3: no se colapsa `execution` con `certification`, ni INCONCLUSIVE con PASS."""
    ejecucion, certificacion = veredicto_de(informe)
    assert ejecucion == "COMPLETE"
    assert certificacion == "PASS"


def test_inconclusive_no_es_pass() -> None:
    """D3. Tratarlo como PASS convierte «no habia nada que medir» en «esta bien»."""
    assert veredicto_de({"execution": "COMPLETE", "certification": "INCONCLUSIVE"}) != (
        "COMPLETE",
        "PASS",
    )


def test_un_aviso_sin_identificador_no_se_traga_en_silencio() -> None:
    """Si el otro lado emitiera un aviso sin `code`, callarlo seria perderlo."""
    with pytest.raises(ValueError, match="sin identificador"):
        avisos_de({"warnings": [{"message": "algo pasó", "reason": "QUIEN_SABE"}]})


def test_un_identificador_de_un_espacio_desconocido_se_delata() -> None:
    """Un espacio nuevo es contrato nuevo: no se interpreta por parecido."""
    with pytest.raises(ValueError, match="SS-NUEVO-001"):
        avisos_de({"warnings": [{"code": "SS-NUEVO-001", "message": "x"}]})


def test_dos_avisos_pueden_compartir_motivo_y_no_identificador() -> None:
    """`SS-PKG-001` y `SS-PKG-003` comparten motivo: el resultado es el mismo y la causa no."""
    avisos = avisos_de(
        {
            "warnings": [
                {"code": "SS-PKG-001", "reason": "RUTA_FUERA_DE_LA_RAIZ", "message": "con .."},
                {"code": "SS-PKG-003", "reason": "RUTA_FUERA_DE_LA_RAIZ", "message": "enlace"},
            ]
        }
    )
    assert avisos == ["SS-PKG-001", "SS-PKG-003"]


def test_ningun_fichero_de_videomesh_decide_mirando_un_mensaje() -> None:
    """La puerta que sujeta D2 de este lado, y se vigila por ausencia.

    Leer `warning["message"]` no rompe ninguna prueba el dia que se escribe: rompe
    el dia que el otro lado cambia una palabra. Ya cambió los treinta y seis
    mensajes de golpe el 2026-09-13, y no rompió nada porque nadie los parseaba.
    """
    codigo = pathlib.Path(__file__).resolve().parents[1] / "src" / "videomesh"
    culpables = [
        ruta.relative_to(codigo).as_posix()
        for ruta in codigo.rglob("*.py")
        if '["message"]' in ruta.read_text(encoding="utf-8")
    ]
    assert culpables == []


# --- La respuesta a los identificadores propuestos --------------------------


def _tabla_de_softsight() -> dict[str, dict[str, str]]:
    """Lee la tabla de identificadores de SoftSight. **Se lee, no se copia.**

    Copiarla aquí sería un segundo original que diverge en el primer código nuevo,
    que es lo mismo que D15 evita con los modelos.
    """
    import re

    fuente = ESQUEMAS.parent / "src" / "soft" / "agent" / "reconstruction" / "codes.ts"
    texto = fuente.read_text(encoding="utf-8")
    tabla: dict[str, dict[str, str]] = {}
    for identificador, cuerpo in re.findall(r'"(SS-[A-Z]+-\d{3})":\s*\{(.*?)\n  \}', texto, re.S):
        motivo = re.search(r'reason:\s*"([^"]+)"', cuerpo)
        estado = re.search(r'status:\s*"([^"]+)"', cuerpo)
        tabla[identificador] = {
            "motivo": motivo.group(1) if motivo else "",
            "estado": estado.group(1) if estado else "",
        }
    return tabla


def test_todos_los_identificadores_publicados_tienen_forma_valida() -> None:
    """Lo que VideoMesh necesita de D2: que sean parseables y de un espacio declarado."""
    tabla = _tabla_de_softsight()
    assert tabla, "no se pudo leer la tabla de SoftSight"
    assert all(es_identificador(i) for i in tabla)


def test_ningun_identificador_esta_repetido() -> None:
    """Un motivo puede repetirse; un identificador es la identidad y no."""
    import re

    fuente = ESQUEMAS.parent / "src" / "soft" / "agent" / "reconstruction" / "codes.ts"
    apariciones = re.findall(r'"(SS-[A-Z]+-\d{3})":\s*\{', fuente.read_text(encoding="utf-8"))
    assert len(apariciones) == len(set(apariciones))


@pytest.mark.parametrize(
    ("identificador", "motivo"),
    [
        ("SS-RECON-003", "TRANSFORMACION_MAL_FORMADA"),
        ("SS-RECON-004", "TRANSFORMACION_NO_RIGIDA"),
        ("SS-RECON-005", "MARCO_INALCANZABLE"),
    ],
)
def test_los_motivos_que_videomesh_emite_son_los_canonicos(identificador: str, motivo: str) -> None:
    """La puerta que hace verificable la respuesta a D2.

    Estos tres motivos se escribieron aquí desde el texto de D11, sin mirar la
    tabla de identificadores, y coinciden con los canónicos palabra por palabra. Que
    dos implementaciones lleguen al mismo vocabulario es lo que hace que fijar estos
    números no sea una preferencia sino un hecho.

    Y si el otro lado renombra uno, esto se pone rojo — que es el caso que D2 dice
    que no debe romper a nadie **solo si lo que se parsea es el identificador**.
    """
    assert _tabla_de_softsight()[identificador]["motivo"] == motivo


def test_los_identificadores_que_videomesh_cita_en_su_codigo_existen() -> None:
    """`SS-RECON-001` y `SS-RECON-002` están escritos en `domain/scale.py` (D9)."""
    tabla = _tabla_de_softsight()
    for identificador in ("SS-RECON-001", "SS-RECON-002"):
        assert identificador in tabla
