"""La línea de órdenes de VideoMesh — §20 del roadmap.

Cuatro órdenes de Core Foundation —crear un proyecto, mirar en qué estado está,
saber si el entorno sirve, y qué habría que rehacer— más el pipeline entero, y la
cadena de producción: `import` trae el paquete que se hace en Colab, y `limpieza`,
`decimado` y `uv` lo acaban aquí, publicando cada una cuánto costó. `retopologia`
está y **falla bien**: falta su proveedor, y sustituirlo daría una etapa de quads que
no dice cuánto costó. `textura` está en las mismas.

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
from typing import Any

from videomesh.adapters import xatlas
from videomesh.application import (
    colision,
    glb_final,
    lod,
    material,
    normales,
    perfiles,
    publicacion,
    retopologia,
    siguiente,
    textura,
    uv,
)
from videomesh.application.cadena import estado_de_la_cadena
from videomesh.application.decimado import decimar
from videomesh.application.densa import importar_paquete
from videomesh.application.limpieza import MINIMO_RELATIVO_POR_DEFECTO, limpiar
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
  videomesh limpieza <ruta> [--minimo-relativo <f>]
                              quita trozos flotantes, triangulos nulos y
                              vertices sueltos, y publica cuanto quito
  videomesh decimado <ruta> --objetivo <n>
                              colapso de aristas hasta n triangulos, y publica
                              la distancia de superficie en las dos direcciones
  videomesh retopologia <ruta>
                              triangulos -> quads alineados. Hoy no se puede:
                              falta el proveedor, y no se sustituye
  videomesh uv <ruta> [--margen <texeles>] [--iteraciones <n>] [--solape-maximo <f>]
                              corta y empaqueta el atlas, escribe el GLB con las
                              coordenadas de textura, y publica el veredicto del
                              informe de produccion de SoftSight sobre ellas
  videomesh normales <ruta> [--resolucion <texeles>] [--sin-relleno]
                              hornea la normal de la malla medida sobre el atlas,
                              y publica el angulo que costo y el juicio del vecino
  videomesh lod <ruta> --niveles <n1,n2,...>
                              encadena los niveles, cada uno decimado del anterior,
                              y publica la distancia de cada paso
  videomesh colision <ruta>
                              construye el casco convexo y le pasa la contencion al
                              vecino, con la holgura declarada en el destino
  videomesh material <ruta>
                              declara el material que ata la pieza y sus mapas, y
                              publica el veredicto del vecino sobre el asset vestido
  videomesh glb <ruta> [--destino <perfil>]
                              empaqueta el asset final con meshoptimizer y KTX2, en
                              dos variantes, y publica el veredicto del vecino sobre
                              la que su cargador puede leer
  videomesh publish <ruta> [--destino <nombre>]
                              sella el paquete de produccion y lo pasa por la QA de
                              SoftSight: PRODUCTION_READY, o UNKNOWN con la lista de
                              lo que falta
  videomesh next <ruta> [--vueltas <n>] [--olvidar]
                              dice que etapa rehacer y con que parametro, sin
                              ejecutarla. Para cuando una vuelta no mejora o la
                              distancia contra la malla medida empeora
  videomesh textura <ruta>
                              proyecta los fotogramas sobre la malla. Hoy no se
                              puede: falta TextureMesh de OpenMVS, y no se sustituye

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


def _banderas(
    argumentos: Sequence[str], conocidas: Sequence[str]
) -> tuple[list[str], dict[str, str]] | None:
    """Separa posicionales de banderas con valor. `None` si una bandera va sin el."""
    posicionales: list[str] = []
    valores: dict[str, str] = {}
    indice = 0
    while indice < len(argumentos):
        actual = argumentos[indice]
        if actual.startswith("--"):
            if actual not in conocidas:
                return None
            if indice + 1 >= len(argumentos):
                return None
            valores[actual] = argumentos[indice + 1]
            indice += 2
            continue
        posicionales.append(actual)
        indice += 1
    return posicionales, valores


def _resumen_de_distancia(medidas: dict[str, Any]) -> str:
    """El numero que dice cuanto se perdio, en una linea y con su estado."""
    distancia = medidas.get("distancia") or {}
    if distancia.get("estado") != "MEDIDA":
        motivo = distancia.get("motivo", "sin motivo declarado")
        return f"  distancia de superficie   NOT_RUN — {motivo}"
    falta = distancia["falta"]
    sobra = distancia["sobra"]
    return (
        f"  distancia de superficie   falta {falta['maximo']:.3e}"
        f" ({falta['fraccion_de_la_diagonal']:.2e} de la diagonal)"
        f" · sobra {sobra['maximo']:.3e} ({sobra['fraccion_de_la_diagonal']:.2e})"
        f" · suelo de ruido {distancia['suelo_de_ruido']:.2e}"
    )


def _limpieza(argumentos: Sequence[str]) -> int:
    """Limpia la malla medida y **dice cuanto quito**."""
    analizado = _banderas(argumentos, ["--minimo-relativo"])
    if analizado is None:
        print("uso: videomesh limpieza <ruta> [--minimo-relativo <fraccion>]")
        return 1
    posicionales, valores = analizado
    if not posicionales:
        print("uso: videomesh limpieza <ruta> [--minimo-relativo <fraccion>]")
        return 1
    try:
        minimo = float(valores.get("--minimo-relativo", MINIMO_RELATIVO_POR_DEFECTO))
    except ValueError:
        print(f"--minimo-relativo espera un numero y recibio {valores['--minimo-relativo']!r}")
        return 1

    informe = limpiar(pathlib.Path(posicionales[0]), minimo_relativo=minimo)
    medidas = json.loads(informe.read_text(encoding="utf-8"))["medidas"]
    print(
        f"limpieza: {medidas['triangulos_antes']} → {medidas['triangulos_despues']} triangulos · "
        f"{medidas['componentes_antes']} → {medidas['componentes_despues']} componentes · "
        f"{medidas['triangulos_degenerados']} nulos y {medidas['vertices_sueltos']} sueltos"
    )
    print(_resumen_de_distancia(medidas))
    print(f"  informe: {informe}")
    return 0


def _decimado(argumentos: Sequence[str]) -> int:
    """Decima hasta un objetivo de triangulos y publica lo que se perdio."""
    analizado = _banderas(argumentos, ["--objetivo"])
    if analizado is None:
        print("uso: videomesh decimado <ruta> --objetivo <triangulos>")
        return 1
    posicionales, valores = analizado
    if not posicionales or "--objetivo" not in valores:
        print("uso: videomesh decimado <ruta> --objetivo <triangulos>")
        return 1
    try:
        objetivo = int(valores["--objetivo"])
    except ValueError:
        print(f"--objetivo espera un numero entero y recibio {valores['--objetivo']!r}")
        return 1

    informe = decimar(pathlib.Path(posicionales[0]), objetivo=objetivo)
    medidas: dict[str, Any] = json.loads(informe.read_text(encoding="utf-8"))["medidas"]
    print(
        f"decimado: {medidas['triangulos_antes']} → {medidas['triangulos_despues']} triangulos "
        f"(objetivo {objetivo})"
    )
    print(_resumen_de_distancia(medidas))
    contra_la_medida = medidas.get("distancia_contra_la_malla_medida")
    if contra_la_medida is not None:
        # Dos numeros y no uno: el de arriba dice cuanto costo decimar, y este cuanto se
        # ha perdido desde el objeto de verdad —limpieza incluida—. Es el freno del loop.
        resumen = _resumen_de_distancia({"distancia": contra_la_medida}).strip()
        print(f"  contra la malla medida      {resumen}")
    print(f"  informe: {informe}")
    return 0


def _retopologia(argumentos: Sequence[str]) -> int:
    """La etapa que hoy no se puede hacer, y lo dice con sus tres partes.

    No se implementa un sustituto: lo unico que el proveedor de malla sabe hacer con
    quads conserva los vertices originales, asi que no alinearia con la forma y no
    tendria ninguna perdida que publicar. El motivo esta en `retopologia.exigir`.
    """
    if not argumentos:
        print("falta la ruta del proyecto: videomesh retopologia <ruta>")
        return 1
    abrir_proyecto(pathlib.Path(argumentos[0]))
    retopologia.exigir()
    print(
        "el proveedor de retopologia esta puesto, pero la etapa no esta escrita: el "
        "encargo la pide desde que su instrumento no estaba en esta maquina"
    )
    return 1


def _material(argumentos: Sequence[str]) -> int:
    """Declara el material y **ensena el veredicto del vecino** sobre el asset vestido."""
    if not argumentos:
        print("uso: videomesh material <ruta>")
        return 1
    informe = material.vestir(pathlib.Path(argumentos[0]))
    documento: dict[str, Any] = json.loads(informe.read_text(encoding="utf-8"))
    declarado = documento["medidas"]["material"]
    canales = ", ".join(f"{canal} -> {fichero}" for canal, fichero in declarado["textures"].items())
    print(
        f"material: {declarado['id']} · pinta maestra · {canales} · "
        f"wrap {declarado['wrap']} · {declarado['alphaMode']}"
    )
    _resumen_del_juicio(documento["veredicto_del_vecino"])
    print(f"  informe: {informe}")
    return 0


def _next(argumentos: Sequence[str]) -> int:
    """Dice qué etapa rehacer y con qué parámetro, y **no la ejecuta**.

    Una línea por fallo, y el techo del bucle delante: si ya se agotaron las vueltas o la
    última no mejoró lo que la motivó, lo que se imprime es la parada. Código 0 cuando
    hay algo que hacer —o cuando no hay nada—, y 2 cuando el bucle para, que no es ni un
    éxito ni un error.
    """
    reiniciar = "--olvidar" in argumentos
    limpios = [argumento for argumento in argumentos if argumento != "--olvidar"]
    analizado = _banderas(limpios, ["--vueltas"])
    if analizado is None or not analizado[0]:
        print("uso: videomesh next <ruta> [--vueltas <n>] [--olvidar]")
        return 1
    posicionales, valores = analizado
    try:
        vueltas = int(valores.get("--vueltas", siguiente.MAX_VUELTAS))
    except ValueError:
        print("hacen falta numeros en --vueltas")
        return 1

    proyecto = pathlib.Path(posicionales[0])
    decision = siguiente.decidir(proyecto, vueltas=vueltas, olvidar=reiniciar)
    if decision.parada is not None:
        print(f"PARA: {decision.parada}")
        return 2
    if not decision.rehacer:
        print("no hay nada que rehacer: la ultima publicacion no deja ningun fallo abierto")
        return 0

    print(f"vueltas dadas: {decision.vueltas} de {vueltas}")
    for rehacer in decision.rehacer:
        print(f"  {rehacer.linea(proyecto)}")
    print("  (esto es lo que habria que rehacer; `next` no lo ejecuta)")
    return 0


def _publish(argumentos: Sequence[str]) -> int:
    """Publica el paquete y **ensena el veredicto de la QA**, o lo que falta.

    El estado sale de su `readiness` y no se interpreta aquí: él decide qué es estar
    listo, y traducir su veredicto daría un segundo criterio del mismo juicio.
    """
    conocidas = ["--destino"]
    analizado = _banderas(argumentos, conocidas)
    if analizado is None or not analizado[0]:
        print("uso: videomesh publish <ruta> [--destino <nombre>]")
        return 1
    posicionales, valores = analizado
    nombre = str(valores.get("--destino", perfiles.DESTINO_POR_DEFECTO))
    informe = publicacion.publicar(
        pathlib.Path(posicionales[0]), destino=perfiles.destino_de_reparto(nombre)
    )
    documento: dict[str, Any] = json.loads(informe.read_text(encoding="utf-8"))
    medidas = documento["medidas"]
    veredicto = medidas["veredicto"]
    perfil = f" · perfil {medidas['perfil']}" if medidas.get("perfil") else ""
    print(f"publicacion: {medidas['paquete']} · destino {medidas['destino']}{perfil}")
    print(f"  artefactos                 {', '.join(medidas['piezas'])}")
    validacion = medidas.get("validacion_externa")
    if validacion is None:
        print("  validador externo          NOT_RUN — sin validador de Khronos")
    else:
        print(
            f"  validador externo          {validacion['proveedor']} {validacion['version']} · "
            f"{validacion['errores']} errores · {validacion['avisos']} avisos"
        )
    print(f"  veredicto de la QA         {veredicto['estado']}")
    for pendiente in veredicto.get("falta", []):
        print(f"    {pendiente['id']}  {pendiente['estado']} — {pendiente['motivo']}")
    if veredicto.get("comando"):
        print(f"  comando                    {veredicto['comando']}")
    _resumen_del_juicio(documento["veredicto_del_vecino"])
    for pendiente in documento.get("no_comprobado", []):
        print(f"  {pendiente['que']}  NOT_RUN — {pendiente['motivo']}")
    print(f"  informe: {informe}")
    return 0


def _glb(argumentos: Sequence[str]) -> int:
    """Empaqueta el asset final y **ensena las dos variantes** y quien juzgo la auditable."""
    conocidas = ["--destino"]
    analizado = _banderas(argumentos, conocidas)
    if analizado is None or not analizado[0]:
        print("uso: videomesh glb <ruta> [--destino <perfil>]")
        return 1
    posicionales, valores = analizado
    nombre = str(valores.get("--destino", perfiles.PERFIL_POR_DEFECTO))
    informe = glb_final.empaquetar(
        pathlib.Path(posicionales[0]), destino=perfiles.destino_declarado(nombre)
    )
    documento: dict[str, Any] = json.loads(informe.read_text(encoding="utf-8"))
    medidas = documento["medidas"]
    for clave in ("sin_ktx2", "con_ktx2"):
        variante = medidas[clave]
        extensiones = ", ".join(variante["extensiones"]) or "ninguna"
        print(
            f"glb: {variante['ruta']} · {variante['triangulos']} tri · "
            f"{variante['bytes'] / 1024:.1f} KB · extensiones {extensiones}"
        )
    _resumen_del_juicio(documento["veredicto_del_vecino"])
    for pendiente in documento.get("no_comprobado", []):
        print(f"  {pendiente['que']}  NOT_RUN — {pendiente['motivo']}")
    print(f"  informe: {informe}")
    return 0


def _lod(argumentos: Sequence[str]) -> int:
    """Encadena los niveles y **ensena la cadena**: un nivel por línea."""
    conocidas = ["--niveles"]
    analizado = _banderas(argumentos, conocidas)
    if analizado is None or not analizado[0]:
        print("uso: videomesh lod <ruta> --niveles <n1,n2,...>")
        return 1
    posicionales, valores = analizado
    bruto = str(valores.get("--niveles", ""))
    try:
        niveles = [int(x) for x in bruto.split(",") if x.strip()]
    except ValueError:
        print("--niveles tiene que ser una lista de numeros separados por comas")
        return 1
    if not niveles:
        print("falta la cadena de niveles: --niveles <n1,n2,...>")
        return 1

    informe = lod.encadenar(pathlib.Path(posicionales[0]), niveles=niveles)
    documento: dict[str, Any] = json.loads(informe.read_text(encoding="utf-8"))
    medidas = documento["medidas"]
    for nivel in medidas["niveles"]:
        falta = nivel["distancia_contra_la_malla_medida"]["falta"]
        print(
            f"nivel {nivel['nivel']}: {nivel['entrada']} -> {nivel['triangulos']} tri · "
            f"contra la medida {falta['maximo']:.3e}"
        )
    if medidas["cadena_parada"]:
        print(f"  cadena parada: {medidas['motivo_de_la_parada']}")
    print(f"  informe: {informe}")
    return 0


def _colision(argumentos: Sequence[str]) -> int:
    """Construye el casco y **ensena el veredicto de contencion** del vecino."""
    if not argumentos:
        print("uso: videomesh colision <ruta>")
        return 1
    informe = colision.construir(
        pathlib.Path(argumentos[0]),
        destino={
            "preset": uv.DESTINO_POR_DEFECTO,
            "budgets": [],
            "collisionSlackMax": 0.10,
            "collisionRequireConvex": True,
        },
    )
    documento: dict[str, Any] = json.loads(informe.read_text(encoding="utf-8"))
    proxy = documento["medidas"]["proxy"]
    print(
        f"colision: casco {proxy['vertices']} v / {proxy['caras']} caras · "
        f"cerrado {'si' if proxy['cerrado'] else 'NO'}"
    )
    _resumen_del_juicio(documento["veredicto_del_vecino"])
    contencion = documento["veredicto_del_vecino"].get("contencion")
    if contencion is not None:
        veredicto_contencion = "PASS" if contencion.get("verdict") == "PASS" else "FAIL"
        asomo = contencion.get("protrudingRatio", 0) * 100
        print(f"  contencion                 {veredicto_contencion} · asomo {asomo:.1f} %")
    print(f"  informe: {informe}")
    return 0


def _textura(argumentos: Sequence[str]) -> int:
    """La etapa que hoy no se puede hacer, y lo dice con sus tres partes.

    No se implementa un sustituto: lo que se interpola desde la nube no es el color
    que vio ninguna camara. El motivo esta en `textura.exigir`.
    """
    if not argumentos:
        print("falta la ruta del proyecto: videomesh textura <ruta>")
        return 1
    abrir_proyecto(pathlib.Path(argumentos[0]))
    textura.exigir()
    print(
        "el proveedor de textura esta puesto, pero la etapa no esta escrita: el encargo "
        "la pide desde que su instrumento no estaba en esta maquina"
    )
    return 1


def _uv(argumentos: Sequence[str]) -> int:
    """Corta y empaqueta el atlas y **ensena el veredicto del vecino** sobre el."""
    conocidas = ["--margen", "--iteraciones", "--destino", "--solape-maximo"]
    analizado = _banderas(argumentos, conocidas)
    if analizado is None or not analizado[0]:
        print(
            "uso: videomesh uv <ruta> [--margen <texeles>] [--iteraciones <n>] "
            "[--destino <nombre>] [--solape-maximo <fraccion>]"
        )
        return 1
    posicionales, valores = analizado
    try:
        margen = int(valores.get("--margen", xatlas.MARGEN_POR_DEFECTO))
        iteraciones = int(valores.get("--iteraciones", xatlas.ITERACIONES_POR_DEFECTO))
        solape = float(valores.get("--solape-maximo", uv.SOLAPE_MAXIMO_POR_DEFECTO))
    except ValueError:
        print("hacen falta numeros en --margen, --iteraciones y --solape-maximo")
        return 1

    informe = uv.cortar_y_empaquetar(
        pathlib.Path(posicionales[0]),
        margen=margen,
        iteraciones=iteraciones,
        destino=valores.get("--destino", uv.DESTINO_POR_DEFECTO),
        solape_maximo=solape,
    )
    medidas: dict[str, Any] = json.loads(informe.read_text(encoding="utf-8"))["medidas"]
    print(
        f"uv: {medidas['islas']} islas · {medidas['vertices_antes']} → "
        f"{medidas['vertices_despues']} vertices ({medidas['vertices_anadidos_por_las_costuras']} "
        f"por las costuras) · {medidas['triangulos']} triangulos"
    )
    print(
        f"  empaquetado {medidas['empaquetado']['ancho']}×{medidas['empaquetado']['alto']} "
        f"(margen {margen}, iteraciones {iteraciones})"
    )
    print(_resumen_de_distancia(medidas))
    contra_la_medida = medidas.get("distancia_contra_la_malla_medida")
    if contra_la_medida is not None:
        resumen = _resumen_de_distancia({"distancia": contra_la_medida}).strip()
        print(f"  contra la malla medida      {resumen}")
    _resumen_del_juicio(json.loads(informe.read_text(encoding="utf-8"))["veredicto_del_vecino"])
    print(f"  informe: {informe}")
    return 0


def _normales(argumentos: Sequence[str]) -> int:
    """Hornea el mapa y **ensena el angulo que costo**, con el juicio del vecino al lado."""
    conocidas = ["--resolucion", "--destino", "--sin-relleno"]
    analizado = _banderas(argumentos, conocidas)
    if analizado is None or not analizado[0]:
        print(
            "uso: videomesh normales <ruta> [--resolucion <texeles>] [--destino <nombre>] "
            "[--sin-relleno]"
        )
        return 1
    posicionales, valores = analizado
    try:
        resolucion = int(valores.get("--resolucion", normales.RESOLUCION_POR_DEFECTO))
    except ValueError:
        print("hacen falta numeros en --resolucion")
        return 1

    informe = normales.hornear(
        pathlib.Path(posicionales[0]),
        resolucion=resolucion,
        pullpush="--sin-relleno" not in valores,
        destino=valores.get("--destino", uv.DESTINO_POR_DEFECTO),
    )
    documento: dict[str, Any] = json.loads(informe.read_text(encoding="utf-8"))
    medidas = documento["medidas"]
    angulo = medidas["angulo"]
    print(
        f"normales: {medidas['atlas']['triangulos']} triangulos sobre un atlas "
        f"{medidas['resolucion']['lado']}×{medidas['resolucion']['lado']}"
    )
    print(
        f"  angulo contra lo pedido      medio {angulo['medio']:.3f}° · p95 {angulo['p95']:.3f}° "
        f"· maximo {angulo['maximo']:.3f}° "
        f"(suelo del formato {angulo['suelo_de_cuantizacion']:.3f}°)"
    )
    paso = medidas["paso_de_la_malla_medida"]
    vecino = medidas["vecino_mas_cercano"]
    print(
        f"  paso de la medida            mediano {paso['mediano']:.6g} · p90 {paso['p90']:.6g} "
        f"({paso['muestras']:.0f} muestras)"
    )
    print(
        f"  vecino mas cercano           mediana {vecino['mediana']:.6g} · "
        f"maxima {vecino['maxima']:.6g}"
    )
    print(_resumen_de_distancia(medidas))
    _resumen_del_juicio(documento["veredicto_del_vecino"])
    print(f"  informe: {informe}")
    return 0


def _resumen_del_juicio(veredicto: dict[str, Any]) -> None:
    """El veredicto del vecino, con sus numeros y no con los nuestros."""
    if veredicto["estado"] != "MEDIDO":
        print(f"  informe del vecino          NOT_RUN — {veredicto['motivo']}")
        return
    motivo = f" · {veredicto['motivo']}" if veredicto.get("motivo") else ""
    print(f"  informe del vecino          {veredicto['certificacion']}{motivo}")
    maestra = veredicto.get("maestra")
    if not maestra:
        return
    medido = maestra["uv"] or {}
    veredictos = maestra.get("veredictos") or {}
    if not medido.get("present"):
        print(f"    uv                        sin coordenadas ({medido.get('reason', '')})")
        return
    print(
        f"    uv                        solape {medido['overlapRatio'] * 100:.1f} % · "
        f"uso {medido['utilization'] * 100:.0f} % · {medido['degenerateTriangles']} degenerados · "
        f"{medido['outsideUnitSquare']} fuera del cuadrado"
    )
    print(f"    veredictos                {veredictos}")


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
    "limpieza": _limpieza,
    "decimado": _decimado,
    "retopologia": _retopologia,
    "uv": _uv,
    "normales": _normales,
    "lod": _lod,
    "material": _material,
    "colision": _colision,
    "glb": _glb,
    "publish": _publish,
    "next": _next,
    "textura": _textura,
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
