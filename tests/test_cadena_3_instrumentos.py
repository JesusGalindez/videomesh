"""`doctor` no decía nada de los instrumentos que la cadena de malla y atlas usa.

Al terminar el bloque B quedaron dos huecos dichos y no arreglados, y los dos eran
del mismo tipo: **una etapa que necesita un instrumento que el informe de entorno no
menciona**. `limpieza` y `decimado` van por `pymeshlab`, que no es un binario de
`PATH` sino un extra de Python; y el número que cierra el encargo lo mide `diffMeshes`
de SoftSight a través de `tools/agent3d.mjs`. Ninguno de los dos aparecía en `doctor`,
así que el día que falte se descubre con una excepción en mitad de la etapa en vez de
en la primera línea del día.

El bloque C añadió dos más, y uno de ellos **no está**: el cortador de atlas es un
extra de Python que sí se instala, y el proveedor de retopología es un programa de
fuera que en esta máquina no se puede ni construir. Los tres tienen su fila, y el que
falta lo dice con la consecuencia escrita —qué etapas se quedan esperando— en vez de
con un «no está».

Van con `bloquea=False`, como COLMAP y FFmpeg, y por la misma razón: el paquete base
—R0, que es JSON, hashes y álgebra— funciona sin ellos. Lo que no se hace es callarlo.

Las comprobaciones reciben sus hechos **por argumento**, así que el caso rojo se
escribe sin desinstalar nada; y las filas del informe se comparan contra el hecho de
hoy en vez de contra una constante, para que la prueba no se rompa el día que alguien
instale el proveedor que falta.
"""

import pathlib
from typing import Any

from videomesh.adapters import pymeshlab, xatlas
from videomesh.adapters.softsight import HERRAMIENTA
from videomesh.application import retopologia
from videomesh.cli.doctor import (
    comprobar_herramienta_de_medida,
    comprobar_proveedor,
    informe_de_doctor,
)

#: Las filas de proveedor que el informe tiene que traer, con su nombre de paquete.
PROVEEDORES = {
    "Proveedor de malla": pymeshlab.PROVEEDOR,
    "Proveedor de UV": xatlas.PROVEEDOR,
    "Proveedor de retopología": retopologia.PROVEEDOR,
}


def _fila(que: str) -> dict[str, Any]:
    informe = informe_de_doctor()
    return next(c for c in informe["comprobaciones"] if c["que"] == que)


# --- los proveedores de las etapas -------------------------------------------


def test_cada_proveedor_de_etapa_tiene_su_propia_fila() -> None:
    """Tres etapas, tres proveedores, y el informe los nombra a los tres.

    La versión viaja en el detalle porque **entra en el hash de entrada** de cada
    etapa (§9): un proveedor nuevo deja el registro describiendo una salida que ya no
    se produciría, y sin el número a la vista eso se lee como una etapa caducada sin
    motivo.
    """
    for que, nombre in PROVEEDORES.items():
        fila = _fila(que)
        if fila["estado"] == "DISPONIBLE":
            assert nombre in str(fila["detalle"])


def test_la_fila_de_cada_proveedor_dice_lo_que_hoy_hay() -> None:
    """Contra el hecho de hoy y no contra una constante: si alguien instala
    `instant-meshes`, la fila tiene que cambiar sola — y esta prueba con ella."""
    for que, _ in PROVEEDORES.items():
        fila = _fila(que)
        instalado = (
            pymeshlab.instalado()
            if que == "Proveedor de malla"
            else xatlas.instalado()
            if que == "Proveedor de UV"
            else retopologia.instalado()
        )
        assert fila["estado"] == ("DISPONIBLE" if instalado else "AUSENTE")


def test_sin_el_proveedor_la_fila_dice_como_se_instala_y_que_espera() -> None:
    """El caso rojo, sin desinstalar nada."""
    fila = comprobar_proveedor(
        "Proveedor de malla",
        nombre="pymeshlab",
        instalado=False,
        version="no instalado",
        instalacion="uv pip install 'videomesh[malla]'",
        para="limpieza, decimado y las etapas de malla que vienen después",
    )
    assert fila.estado == "AUSENTE"
    assert "uv pip install 'videomesh[malla]'" in fila.detalle
    # Y qué etapas se quedan esperando: sin esto, quien lee la línea no sabe si puede
    # seguir trabajando o no.
    assert "limpieza" in fila.detalle and "decimado" in fila.detalle


def test_la_fila_del_proveedor_que_falta_dice_que_no_se_sustituye() -> None:
    """El de retopología es el único que hoy falta, y su fila lo declara como ausencia
    declarada y no como rotura: es la diferencia entre «no se puede» y «no lo hemos
    puesto»."""
    fila = comprobar_proveedor(
        "Proveedor de retopología",
        nombre=retopologia.PROVEEDOR,
        instalado=False,
        version="",
        instalacion=retopologia.INSTALACION,
        para="convertir triángulos en quads alineados con la forma",
    )
    assert fila.estado == "AUSENTE"
    assert "quads" in fila.detalle
    # Y la instalación dice la verdad de este repositorio: son fuentes, no un gestor
    # de paquetes que aquí no existe.
    assert "fuente" in fila.detalle


def test_faltar_un_proveedor_no_bloquea_lo_que_hoy_no_lo_necesita() -> None:
    """La misma regla que COLMAP y FFmpeg: se reporta, no se convierte en fallo.

    El paquete base —R0, que es JSON, hashes y álgebra— no toca una malla.
    """
    fila = comprobar_proveedor(
        "Proveedor de malla",
        nombre="pymeshlab",
        instalado=False,
        version="no instalado",
        instalacion="uv pip install 'videomesh[malla]'",
        para="limpieza, decimado y las etapas de malla que vienen después",
    )
    assert fila.bloquea is False


def test_el_informe_sigue_siendo_verde_con_los_proveedores_instalados() -> None:
    """Las filas se añaden sin cambiar el veredicto del entorno de hoy."""
    assert informe_de_doctor()["listo"] is True


# --- la herramienta que mide -------------------------------------------------


def test_la_herramienta_de_medida_tiene_su_propia_fila() -> None:
    """El cierre del encargo entero se apoya en este fichero.

    `distancia_de_superficie` ya levanta `MedicionNoDisponible` cuando no está, y
    eso es correcto: la etapa publica NOT_RUN con su motivo. Lo que faltaba es
    saberlo **antes** de correr la etapa, que es para lo que existe `doctor`.
    """
    fila = _fila("SoftSight, herramienta de medida")
    assert fila["estado"] == "DISPONIBLE"
    assert str(HERRAMIENTA) in str(fila["detalle"])


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
