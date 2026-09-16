"""La línea de órdenes de VideoMesh — §20 del roadmap.

Cuatro órdenes de Core Foundation —crear un proyecto, mirar en qué estado está,
saber si el entorno sirve, y qué habría que rehacer— más el pipeline entero, y la
puerta por la que entra la malla densa que se hace en Colab.

De los cuatro stages **hoy solo `produce` puede trabajar**: FFmpeg y COLMAP no
están en esta máquina. Los otros tres existen igual, y esto es un cambio de
criterio respecto a la primera versión de este fichero, que decía que una orden
que no hace nada es peor que una ausente. Sigue siendo verdad de una orden que
calla; no lo es de una que falla diciendo qué le falta, para qué y cómo se
instala. Ausente, el usuario cree que se equivocó de nombre.

Los códigos de salida son los de siempre: 0 si salió, 1 si no. El repertorio de
D13 —20, 21, 23— es del consumidor y no de esta CLI; usarlos aquí para otra cosa
haría ambiguo lo que ya significa algo.
"""

import json
import pathlib
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence

from videomesh.application.cadena import estado_de_la_cadena
from videomesh.application.densa import importar_paquete
from videomesh.application.pipeline import PAQUETES, STAGES, ejecutar_stage, hash_de_entrada
from videomesh.cli.doctor import informe_de_doctor
from videomesh.contracts.generacion import ESQUEMAS
from videomesh.contracts.serialization import volcar_json
from videomesh.domain.errores import ErrorDeVideoMesh
from videomesh.domain.project import preparacion_de
from videomesh.domain.stage import hay_que_reejecutar
from videomesh.project.procedencia import ultima_de_la_etapa
from videomesh.project.stages import historial_de
from videomesh.project.store import abrir_proyecto, crear_proyecto

__all__ = ["main"]

_AYUDA = """videomesh — productor de paquetes de reconstruccion

  videomesh init <ruta>       crea un proyecto
  videomesh status <ruta>     en que estado esta y para que esta preparado
  videomesh doctor [--json]   si el entorno sirve, y para que
  videomesh resume <ruta>     que stages habria que rehacer, y por que

El pipeline:

  videomesh analyze <ruta>    video -> frames            necesita FFmpeg
  videomesh build <ruta>      frames -> dispersa         necesita COLMAP
  videomesh reconstruct <r>   dispersa -> malla          necesita COLMAP
  videomesh produce <ruta>    malla -> paquete sellado
  videomesh validate <ruta>   pasa el paquete por el consumidor de SoftSight

Los tres primeros fallan diciendo que les falta: `videomesh doctor` lo dice todo
de una vez.

La cadena de produccion:

  videomesh import <ruta> <paquete> [--maquina <nombre>]
                              registra el paquete que llega de Colab como la
                              etapa densa, comprobando su integridad

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
    # La cadena, etapa a etapa: que esta hecho, que caduco y que toca. Un stage
    # COMPLETE cuya entrada cambio no esta hecho, esta caducado, y `status` es
    # donde alguien se entera de eso.
    for paso in estado_de_la_cadena(ruta):
        print(f"  {paso.etapa:<11} {paso.situacion.value:<9} {paso.motivo}")
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
        # Contra la entrada de HOY, no contra la que aquella ejecucion tenia:
        # comparar un hash consigo mismo diria «vigente» siempre, que es lo
        # contrario de lo que §11 pide — un COMPLETE cuya entrada cambio esta
        # caducado, no hecho.
        rehacer = hay_que_reejecutar(
            ultima, hash_de_entrada=hash_de_entrada(ruta), semilla=ultima.semilla
        )
        print(f"{stage}  {ultima.estado.value:<9} {'rehacer' if rehacer else 'vigente'}")
    return 0


def _stage(nombre: str) -> Callable[[Sequence[str]], int]:
    """Cada stage del pipeline es la misma orden con otro nombre dentro."""

    def orden(argumentos: Sequence[str]) -> int:
        if not argumentos:
            print(f"falta la ruta del proyecto: videomesh {nombre} <ruta>")
            return 1
        salida = ejecutar_stage(pathlib.Path(argumentos[0]), nombre)
        print(f"{nombre}: {salida}")
        return 0

    return orden


def _validate(argumentos: Sequence[str]) -> int:
    """Pasa el paquete por el consumidor **de verdad**, que es la única puerta.

    D1: se le da la ruta del manifest. Nunca base64, nunca el contenido por la
    entrada estandar.
    """
    if not argumentos:
        print("falta la ruta del proyecto: videomesh validate <ruta>")
        return 1
    ruta = pathlib.Path(argumentos[0])
    abrir_proyecto(ruta)

    manifest = ruta / PAQUETES / "cube-v1" / "manifest.json"
    if not manifest.is_file():
        print(f"no hay paquete en {ruta}: escribelo antes con `videomesh produce {ruta}`")
        return 1

    consumidor = ESQUEMAS.parent / "tools" / "reconstruction.mjs"
    if shutil.which("node") is None or not consumidor.is_file():
        print("falta el consumidor de SoftSight o node; `videomesh doctor` dice cual")
        return 1

    ejecucion = subprocess.run(
        ["node", str(consumidor), "inspect", str(manifest)],
        capture_output=True,
        text=True,
        check=False,
    )
    if ejecucion.returncode != 0:
        print(ejecucion.stderr.strip() or ejecucion.stdout.strip())
        return 1

    informe = json.loads(ejecucion.stdout)
    # Los dos ejes, sin colapsar (D3): INCONCLUSIVE no es PASS.
    print(f"{informe['execution']} + {informe['certification']}")
    for aviso in informe.get("warnings", []):
        print(f"  {aviso.get('code', 'SIN-CODIGO')}  {aviso.get('reason', '')}")
    return 0


def _import(argumentos: Sequence[str]) -> int:
    """Registra un paquete producido fuera como la salida de la etapa `densa`.

    No lo reejecuta: lo comprueba. La densa exige CUDA y llega de Colab, asi que
    lo unico que este lado puede hacer con ella es negarse a creersela sin mirar.
    """
    posicionales: list[str] = []
    maquina: str | None = None
    indice = 0
    while indice < len(argumentos):
        actual = argumentos[indice]
        if actual == "--maquina":
            if indice + 1 >= len(argumentos):
                print("falta el nombre de la maquina: --maquina <nombre>")
                return 1
            maquina = argumentos[indice + 1]
            indice += 2
            continue
        posicionales.append(actual)
        indice += 1

    if len(posicionales) < 2:
        print("uso: videomesh import <proyecto> <paquete> [--maquina <nombre>]")
        return 1

    ruta = pathlib.Path(posicionales[0])
    informe = importar_paquete(ruta, pathlib.Path(posicionales[1]), maquina=maquina)
    anotada = ultima_de_la_etapa(ruta, "densa")
    assert anotada is not None  # lo acaba de anotar el import
    print(f"densa: {anotada.package_id} importada de {anotada.maquina}")
    print(f"  informe: {informe}")
    return 0


_ORDENES: dict[str, Callable[[Sequence[str]], int]] = {
    "init": _init,
    "status": _status,
    "doctor": _doctor,
    "resume": _resume,
    "validate": _validate,
    **{nombre: _stage(nombre) for nombre in STAGES},
    "import": _import,
}


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
