"""Encargo 04, bloque F — `videomesh next` y el techo del bucle.

`next` es lo que hace que esto sea una cadena y no una lista de comandos: lee el último
informe y dice **qué etapa rehacer y con qué parámetro**, sin ejecutarla. Una línea por
fallo, con la medida, su valor y su sitio. Un agente lo lee y decide; una persona
también.

Y el techo, que es obligatorio: un bucle que reintenta sin límite acaba decimando a cero
para cumplir un presupuesto. Dos reglas, y las dos se prueban aquí:

```text
un maximo de vueltas, declarado
si una vuelta no mejora la medida que la motivo, PARA y lo dice
```

Lo segundo es lo que impide el desastre silencioso —bajar triángulos hasta pasar la
puerta habiendo destruido el objeto—, y **el freno es la distancia de superficie contra
la malla medida**, que se publica en cada etapa desde B2. Una vuelta que mejora los
triángulos y empeora esa distancia para el bucle con los dos números delante: seguir es
una decisión de quien lee, no un descuido de la máquina.
"""

import json
import math
import pathlib
from typing import Any

from videomesh.application import perfiles
from videomesh.application.decimado import decimar
from videomesh.application.densa import importar_paquete
from videomesh.application.glb_final import empaquetar
from videomesh.application.limpieza import limpiar
from videomesh.application.normales import hornear
from videomesh.application.publicacion import publicar
from videomesh.application.siguiente import MAX_VUELTAS, decidir
from videomesh.application.uv import cortar_y_empaquetar
from videomesh.cli.app import main
from videomesh.domain.malla import Malla
from videomesh.formatos.ply import escribir_ply_malla
from videomesh.project.bucle import Intento, anotar_intento
from videomesh.project.sellado import publicar_paquete
from videomesh.project.store import crear_proyecto


def _plano_con_bulto(*, divisiones: int = 16) -> Malla:
    """La malla de las pruebas de `normales`, `material` y `publicacion`."""
    vertices: list[tuple[float, float, float]] = []
    for j in range(divisiones + 1):
        for i in range(divisiones + 1):
            x = i / divisiones - 0.5
            y = j / divisiones - 0.5
            radio = math.sqrt(x * x + y * y)
            z = 0.06 * math.exp(-(radio * radio) / 0.12)
            vertices.append((x, y, z))
    triangulos: list[tuple[int, int, int]] = []
    ancho = divisiones + 1
    for j in range(divisiones):
        for i in range(divisiones):
            a = j * ancho + i
            triangulos += [(a, a + 1, a + ancho + 1), (a, a + ancho + 1, a + ancho)]
    return Malla(vertices=vertices, triangulos=triangulos)


def _proyecto(tmp_path: pathlib.Path, *, objetivo: int = 200) -> pathlib.Path:
    """La cadena hasta `glb`, que es lo que la publicación necesita."""
    proyecto = tmp_path / "proyecto"
    crear_proyecto(proyecto, nombre="prueba")
    paquete = tmp_path / "densa-0001"
    with publicar_paquete(paquete, package_id="densa-0001", producer="producers/colmap") as obra:
        escribir_ply_malla(obra.raiz / "malla.ply", _plano_con_bulto())
        obra.anadir("malla.ply", identidad="malla", tipo="TRIANGLE_MESH", purely_reconstructed=True)
        obra.manifest["requiredEvidence"] = ["malla"]
    importar_paquete(proyecto, paquete, maquina="colab-t4")
    limpiar(proyecto)
    decimar(proyecto, objetivo=objetivo)
    cortar_y_empaquetar(proyecto)
    hornear(proyecto, resolucion=256)
    empaquetar(proyecto, destino=perfiles.destino_declarado("hero"))
    return proyecto


def _destino_con_presupuesto(maximo: int) -> dict[str, Any]:
    """Un destino legible y con un tope de triángulos que el asset no cumple."""
    return {
        "preset": "tope-ajustado",
        "budgets": [{"name": "triangulos", "units": "ABSOLUTE", "max": maximo}],
        "textureMaxSize": 256,
        "uvRequired": True,
    }


# --- F1: qué rehacer, y con qué parámetro ---------------------------------------


def test_sin_publicacion_propone_publicar(tmp_path: pathlib.Path) -> None:
    """Sin informe de QA, lo que falta es el paquete: `next` no adivina fallos."""
    proyecto = _proyecto(tmp_path)
    decision = decidir(proyecto)
    assert decision.parada is None
    etapas = [rehacer.etapa for rehacer in decision.rehacer]
    assert etapas == ["publicacion"]
    assert "--destino" in decision.rehacer[0].comando(proyecto)


def test_el_presupuesto_excedido_propone_decimado_con_su_tope(tmp_path: pathlib.Path) -> None:
    """La línea del encargo: la medida, su valor, su tope y el comando que lo arregla."""
    proyecto = _proyecto(tmp_path)
    publicar(proyecto, destino=_destino_con_presupuesto(100))

    decision = decidir(proyecto)
    assert decision.parada is None
    assert len(decision.rehacer) == 1
    rehacer = decision.rehacer[0]
    assert rehacer.etapa == "decimado"
    assert rehacer.parametros == {"objetivo": 100}
    assert rehacer.valor == 200.0
    assert rehacer.limite == 100.0
    linea = rehacer.linea(proyecto)
    assert "200" in linea and "100" in linea
    assert "--objetivo 100" in linea


def test_el_destino_que_no_declara_lo_dice_y_no_lo_tapa(tmp_path: pathlib.Path) -> None:
    """Un tope sin declarar no es un fallo del asset: `next` nombra la publicación."""
    proyecto = _proyecto(tmp_path)
    publicar(proyecto, destino={"preset": "mudo", "budgets": []})

    decision = decidir(proyecto)
    etapas = [rehacer.etapa for rehacer in decision.rehacer]
    assert "publicacion" in etapas
    assert any("no declara" in rehacer.motivo for rehacer in decision.rehacer)


def test_cuando_no_hay_nada_que_rehacer_lo_dice(tmp_path: pathlib.Path) -> None:
    """Publicado y aprobado: `next` no inventa trabajo."""
    proyecto = _proyecto(tmp_path)
    publicar(proyecto, destino=perfiles.destino_de_reparto("web"))

    decision = decidir(proyecto)
    assert decision.rehacer == ()
    assert decision.parada is None


# --- F2: el techo, y el freno ---------------------------------------------------


def test_una_vuelta_que_no_mejora_para_el_bucle(tmp_path: pathlib.Path) -> None:
    """Lo que impide reintentar lo mismo esperando otro resultado."""
    proyecto = _proyecto(tmp_path)
    publicar(proyecto, destino=_destino_con_presupuesto(100))

    primera = decidir(proyecto)
    assert primera.rehacer and primera.parada is None

    # Nadie ha hecho nada: la medida que la motivó sigue igual.
    segunda = decidir(proyecto)
    assert segunda.rehacer == ()
    assert segunda.parada is not None
    assert "triangulos" in segunda.parada


def test_el_techo_de_vueltas_esta_declarado_y_para(tmp_path: pathlib.Path) -> None:
    """Un máximo de vueltas, y se declara: el bucle no se agota en silencio."""
    proyecto = _proyecto(tmp_path)
    publicar(proyecto, destino=_destino_con_presupuesto(100))
    for vuelta in range(MAX_VUELTAS):
        anotar_intento(
            proyecto,
            Intento(
                medida="triangulos",
                valor=float(1000 - vuelta),
                limite=100.0,
                etapa="decimado",
                parametros={"objetivo": 100},
                distancia=0.001,
            ),
        )

    decision = decidir(proyecto)
    assert decision.rehacer == ()
    assert decision.parada is not None
    assert str(MAX_VUELTAS) in decision.parada


def test_el_freno_es_la_distancia_contra_la_malla_medida(tmp_path: pathlib.Path) -> None:
    """Una vuelta que mejora los triángulos y **empeora** la distancia para el bucle.

    Es el desastre silencioso que F2 existe para impedir: bajar triángulos hasta pasar
    la puerta habiendo destruido el objeto. Los dos números viajan en la parada, así que
    seguir a partir de aquí es una decisión de quien lee.
    """
    proyecto = _proyecto(tmp_path)
    destino = _destino_con_presupuesto(10)
    publicar(proyecto, destino=destino)
    primera = decidir(proyecto)
    assert primera.parada is None and primera.rehacer

    # La vuelta que la máquina pediría, entera: menos triángulos y todo lo que cuelga
    # de ellos —el atlas, el horneado y el paquete—, que es el viaje de verdad.
    decimar(proyecto, objetivo=60)
    cortar_y_empaquetar(proyecto)
    hornear(proyecto, resolucion=256)
    empaquetar(proyecto, destino=perfiles.destino_declarado("hero"))
    publicar(proyecto, destino=destino)

    segunda = decidir(proyecto)
    assert segunda.rehacer == ()
    assert segunda.parada is not None
    assert "distancia" in segunda.parada


def test_olvidar_reinicia_las_vueltas(tmp_path: pathlib.Path) -> None:
    """Seguir después de una parada es una decisión explícita, y se pide."""
    proyecto = _proyecto(tmp_path)
    publicar(proyecto, destino=_destino_con_presupuesto(100))
    decidir(proyecto)
    assert decidir(proyecto).parada is not None

    reiniciado = decidir(proyecto, olvidar=True)
    assert reiniciado.parada is None
    assert reiniciado.rehacer


# --- la orden -------------------------------------------------------------------


def test_la_orden_next_ensena_las_lineas(tmp_path: pathlib.Path, capsys: Any) -> None:
    """`videomesh next` imprime qué hacer y no lo hace."""
    proyecto = _proyecto(tmp_path)
    publicar(proyecto, destino=_destino_con_presupuesto(100))

    assert main(["next", str(proyecto)]) == 0
    salida = capsys.readouterr().out
    assert "decimado" in salida
    assert "--objetivo 100" in salida
    # Y no lo ha hecho: el informe del decimado sigue siendo el de antes.
    informe = json.loads((proyecto / "etapas" / "decimado" / "informe.json").read_text())
    assert informe["medidas"]["triangulos_despues"] == 200


def test_la_orden_next_para_con_codigo_propio(tmp_path: pathlib.Path, capsys: Any) -> None:
    """Una parada no es un error ni un éxito: tiene su código, y su motivo."""
    proyecto = _proyecto(tmp_path)
    publicar(proyecto, destino=_destino_con_presupuesto(100))
    assert main(["next", str(proyecto)]) == 0
    assert main(["next", str(proyecto)]) == 2
    assert "PARA" in capsys.readouterr().out
