"""`doctor` no decía nada de los dos instrumentos que la cadena de malla usa.

Al terminar el bloque B quedaron dos huecos dichos y no arreglados, y los dos son
del mismo tipo: **una etapa que necesita un instrumento que el informe de entorno
no menciona**. `limpieza` y `decimado` van por `pymeshlab`, que no es un binario de
`PATH` sino un extra de Python; y el número que cierra el encargo lo mide
`diffMeshes` de SoftSight a través de `tools/agent3d.mjs`. Ninguno de los dos
aparecía en `doctor`, así que el día que falte se descubre con una excepción en
mitad de la etapa en vez de en la primera línea del día.

Va con `bloquea=False`, como COLMAP y FFmpeg, y por la misma razón: el paquete base
—R0, que es JSON, hashes y álgebra— funciona sin ellos. Lo que no se hace es
callarlo: una fila AUSENTE dice qué etapas se quedan esperando.

Las dos comprobaciones reciben sus hechos **por argumento**, así que el caso rojo
se escribe sin desinstalar nada.
"""

import pathlib

from videomesh.adapters.softsight import HERRAMIENTA
from videomesh.cli.doctor import (
    comprobar_herramienta_de_medida,
    comprobar_proveedor_de_malla,
    informe_de_doctor,
)

# --- el proveedor de malla de las etapas B y C ------------------------------


def test_el_proveedor_de_malla_tiene_su_propia_fila() -> None:
    """Hoy está instalado, así que la fila dice DISPONIBLE y con qué versión.

    La versión no es adorno: entra en el hash de entrada de cada etapa, y dos
    versiones distintas dan dos salidas que no se pueden comparar.
    """
    informe = informe_de_doctor()
    fila = next(c for c in informe["comprobaciones"] if c["que"] == "Proveedor de malla")
    assert fila["estado"] == "DISPONIBLE"
    assert "pymeshlab" in fila["detalle"]


def test_sin_el_proveedor_la_fila_dice_como_se_instala_y_que_espera() -> None:
    """El caso rojo, sin desinstalar nada."""
    fila = comprobar_proveedor_de_malla(
        instalado=False,
        version="no instalado",
        instalacion="uv pip install 'videomesh[malla]'",
    )
    assert fila.estado == "AUSENTE"
    assert "uv pip install 'videomesh[malla]'" in fila.detalle
    # Y qué etapas se quedan esperando: sin esto, quien lee la línea no sabe si
    # puede seguir trabajando o no.
    assert "limpieza" in fila.detalle and "decimado" in fila.detalle


def test_faltar_el_proveedor_no_bloquea_lo_que_hoy_no_lo_necesita() -> None:
    """La misma regla que COLMAP y FFmpeg: se reporta, no se convierte en fallo.

    El paquete base —R0, que es JSON, hashes y álgebra— no toca una malla.
    """
    fila = comprobar_proveedor_de_malla(
        instalado=False, version="no instalado", instalacion="uv pip install 'videomesh[malla]'"
    )
    assert fila.bloquea is False


def test_el_informe_sigue_siendo_verde_con_el_proveedor_instalado() -> None:
    """La fila se añade sin cambiar el veredicto del entorno de hoy."""
    assert informe_de_doctor()["listo"] is True


# --- la herramienta que mide -------------------------------------------------


def test_la_herramienta_de_medida_tiene_su_propia_fila() -> None:
    """El cierre del encargo entero se apoya en este fichero.

    `distancia_de_superficie` ya levanta `MedicionNoDisponible` cuando no está, y
    eso es correcto: la etapa publica NOT_RUN con su motivo. Lo que faltaba es
    saberlo **antes** de correr la etapa, que es para lo que existe `doctor`.
    """
    informe = informe_de_doctor()
    fila = next(
        c for c in informe["comprobaciones"] if c["que"] == "SoftSight, herramienta de medida"
    )
    assert fila["estado"] == "DISPONIBLE"
    assert str(HERRAMIENTA) in fila["detalle"]


def test_sin_la_herramienta_la_fila_dice_donde_se_espera(tmp_path: pathlib.Path) -> None:
    """El caso rojo sin tocar SoftSight: se le pasa una ruta que no existe."""
    fila = comprobar_herramienta_de_medida(tmp_path / "agent3d.mjs")
    assert fila.estado == "AUSENTE"
    assert "agent3d.mjs" in fila.detalle
    # La consecuencia, dicha: sin ella la etapa no puede publicar su número.
    assert "NOT_RUN" in fila.detalle


def test_la_herramienta_ausente_no_es_un_fallo_de_hoy(tmp_path: pathlib.Path) -> None:
    """Una etapa sin instrumento publica NOT_RUN, que es un estado legítimo.

    Bloquear `doctor` por esto convertiría «no se pudo medir» en «no se puede
    trabajar», y son dos cosas distintas.
    """
    fila = comprobar_herramienta_de_medida(tmp_path / "agent3d.mjs")
    assert fila.bloquea is False
