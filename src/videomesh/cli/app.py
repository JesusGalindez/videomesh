"""La línea de órdenes de VideoMesh — §20 del roadmap.

Cuatro órdenes hoy, y las cuatro son de Core Foundation: crear un proyecto, mirar
en qué estado está, saber si el entorno sirve, y qué habría que rehacer. Las del
pipeline —`analyze`, `build`, `reconstruct`, `produce`— llegan con sus etapas; una
orden que existe y no hace nada es peor que una que no está.

Los códigos de salida son los de siempre: 0 si salió, 1 si no. El repertorio de
D13 —20, 21, 23— es del consumidor y no de esta CLI; usarlos aquí para otra cosa
haría ambiguo lo que ya significa algo.
"""

import pathlib
import sys
from collections.abc import Sequence

from videomesh.cli.doctor import informe_de_doctor
from videomesh.contracts.serialization import volcar_json
from videomesh.domain.errores import ErrorDeVideoMesh
from videomesh.domain.project import preparacion_de
from videomesh.domain.stage import hay_que_reejecutar
from videomesh.project.stages import historial_de
from videomesh.project.store import abrir_proyecto, crear_proyecto

__all__ = ["main"]

_AYUDA = """videomesh — productor de paquetes de reconstruccion

  videomesh init <ruta>       crea un proyecto
  videomesh status <ruta>     en que estado esta y para que esta preparado
  videomesh doctor [--json]   si el entorno sirve, y para que
  videomesh resume <ruta>     que stages habria que rehacer, y por que

La frontera con SoftSight manda sobre todo lo demas: docs/contrato-videomesh.md.
"""


def _init(argumentos: Sequence[str]) -> int:
    if not argumentos:
        print("falta la ruta del proyecto: videomesh init <ruta>")
        return 1
    ruta = pathlib.Path(argumentos[0])
    proyecto = crear_proyecto(ruta, nombre=argumentos[1] if len(argumentos) > 1 else ruta.name)
    print(f"proyecto {proyecto.nombre} creado en {ruta}")
    return 0


def _status(argumentos: Sequence[str]) -> int:
    if not argumentos:
        print("falta la ruta del proyecto: videomesh status <ruta>")
        return 1
    ruta = pathlib.Path(argumentos[0])
    proyecto = abrir_proyecto(ruta)
    preparado = preparacion_de(proyecto)
    print(f"{proyecto.nombre} — {proyecto.estado.value}")
    print(f"artifacts   {', '.join(proyecto.artifacts) if proyecto.artifacts else 'ninguno'}")
    print(
        "preparado para   "
        + (", ".join(p.value for p in preparado) if preparado else "nada todavia")
    )
    historial = historial_de(ruta)
    print(f"stages      {len(historial)} ejecuciones registradas")
    return 0


def _doctor(argumentos: Sequence[str]) -> int:
    informe = informe_de_doctor()
    if "--json" in argumentos:
        print(volcar_json(informe))
        return 0 if informe["listo"] else 1

    ancho = max(len(c["que"]) for c in informe["comprobaciones"])
    for comprobacion in informe["comprobaciones"]:
        marca = " " if comprobacion["estado"] in ("DISPONIBLE", "COINCIDE", "COMPATIBLE") else "!"
        print(f"{marca} {comprobacion['que']:<{ancho}}  {comprobacion['estado']}")
        if comprobacion["detalle"]:
            print(f"  {'':<{ancho}}  {comprobacion['detalle']}")
    print()
    if informe["listo"]:
        print("lo que R0 necesita esta. COLMAP y FFmpeg son del Sprint 2.")
    else:
        print("falta algo que si bloquea: mira las filas con `!`.")
    return 0 if informe["listo"] else 1


def _resume(argumentos: Sequence[str]) -> int:
    if not argumentos:
        print("falta la ruta del proyecto: videomesh resume <ruta>")
        return 1
    ruta = pathlib.Path(argumentos[0])
    abrir_proyecto(ruta)
    historial = historial_de(ruta)
    if not historial:
        print("sin ejecuciones registradas: no hay nada que reanudar")
        return 0

    ultimas = {ejecucion.stage: ejecucion for ejecucion in historial}
    for stage, ultima in ultimas.items():
        # Con el hash de entrada que ya tenia: lo que se comprueba aqui es si esa
        # ejecucion sigue valiendo por si misma, no si la entrada cambio — eso lo
        # sabra el pipeline cuando exista.
        rehacer = hay_que_reejecutar(
            ultima, hash_de_entrada=ultima.hash_de_entrada, semilla=ultima.semilla
        )
        print(f"{stage}  {ultima.estado.value:<9} {'rehacer' if rehacer else 'vigente'}")
    return 0


_ORDENES = {"init": _init, "status": _status, "doctor": _doctor, "resume": _resume}


def main(argumentos: Sequence[str] | None = None) -> int:
    """Punto de entrada. Devuelve el código de salida en vez de salir él."""
    argumentos = list(sys.argv[1:] if argumentos is None else argumentos)

    if not argumentos:
        print(_AYUDA)
        return 1
    if argumentos[0] in ("--help", "-h", "help"):
        print(_AYUDA)
        return 0

    orden = _ORDENES.get(argumentos[0])
    if orden is None:
        print(f"no existe la orden {argumentos[0]!r}\n")
        print(_AYUDA)
        return 1

    try:
        return orden(argumentos[1:])
    except ErrorDeVideoMesh as error:
        # Lo tipado se cuenta; lo que no lo esté, que suba: un fallo que nadie
        # previó no debe salir disfrazado de error de uso.
        print(str(error))
        return 1
