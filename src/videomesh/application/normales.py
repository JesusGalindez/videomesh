"""La etapa `normales`: el detalle que el decimado quito, de vuelta como mapa — bloque D.

El decimado tiro triangulos y con ellos se fue el relieve. Esta etapa lo devuelve como
una imagen que se lee **contra la superficie**, y lo que publica es lo que ese viaje
costo:

```text
el angulo entre el vector que se pidio hornear y el que quedo en el fichero
las dos distancias de superficie, contra su entrada y contra la malla medida
la desviacion de normales de esas dos distancias, que las mide el vecino
la resolucion, el texel y el paso de la malla medida, que es lo que decide si la
aproximacion del vecino se puede despreciar
el veredicto de R13 sobre el mapa, con sus tres numeros
```

**La decision abierta del encargo, escrita.** El encargo deja elegir entre hacer el
horneado aqui en Python o llamar al trazador de rayos del vecino por el puente. La
elegida es la tercera, y esta razonada en `adapters/geometria.py`: la correspondencia
—que punto de la medida le toca a cada vertice— se resuelve aqui con un vecino mas
cercano probado contra fuerza bruta, la rasterizacion texel a texel la hace el
proveedor de malla, y la medida y el juicio siguen siendo del vecino. No hay un
segundo trazador de rayos en Python y no hay una orden nueva que mantener alli.

**El marco no se promete, se construye y se comprueba.** El mapa se escribe en el
espacio de la UV —tangente, bitangente, normal del vertice, sacados de la derivada de
la posicion respecto de la UV— y si eso estuviera mal el mapa saldria con el relieve
girado, que es un fallo que se ve en el resultado y no en el proceso. Por eso la etapa
publica cuantos triangulos tienen la UV **reflejada**: son los unicos donde el marco
de la UV y el que un visor deriva con el bit de handedness de la especificacion no
coinciden.

**Lo que esta etapa no hace.** No juzga el mapa: eso es R13 del vecino, y su auditoria
es la que dice si lo que se horneo parece un mapa de normales en espacio tangente. Un
mapa en espacio de objeto —que es lo que el proveedor escribe cuando se le pide su
propia normal— **se lee sin error** y sale con relieve absurdo, y por eso su juicio es
el que cierra la etapa.
"""

import pathlib
import time
from typing import Any

from videomesh.adapters import geometria, glb, pymeshlab, softsight
from videomesh.application import uv
from videomesh.application.etapas import medir_distancia, memoria_maxima_mb
from videomesh.application.limpieza import malla_importada
from videomesh.application.trabajo import malla_de_trabajo
from videomesh.contracts.serialization import volcar_json
from videomesh.domain.errores import ErrorDeProyecto, MedicionNoDisponible
from videomesh.domain.procedencia import EstadoDeProcedencia, Procedencia
from videomesh.domain.stage import (
    Determinismo,
    EjecucionDeStage,
    EstadoDeStage,
    hash_de_entrada,
    hay_que_reejecutar,
)
from videomesh.formatos.obj import escribir_obj_coloreado
from videomesh.project import activo
from videomesh.project.informe import (
    INFORME,
    describir_malla,
    directorio_de_etapa,
    escribir_informe,
    leer_informe,
    malla_de_la_etapa,
    salida_de,
)
from videomesh.project.procedencia import anotar_procedencia
from videomesh.project.stages import registrar_stage, ultima_de
from videomesh.project.store import abrir_proyecto

__all__ = [
    "ETAPA",
    "GLB",
    "MAPA",
    "RESOLUCION_POR_DEFECTO",
    "angulo_entre",
    "digest_de_la_entrada",
    "hornear",
    "sha_de_la_entrada",
    "suelo_de_cuantizacion_grados",
]

ETAPA = "normales"

PRODUCTOR = "videomesh/normales"

#: El mapa horneado. El vecino lo busca por su papel en el manifiesto, y este es el
#: fichero que ese papel declara.
MAPA = "normales.png"

#: La pieza con su normal y su atlas. Es la que la etapa de material va a vestir.
GLB = "malla.glb"

#: El nombre de la malla dentro del manifiesto, igual que en la etapa de UV.
IDENTIDAD_DE_LA_MAESTRA = "maestra"

#: El OBJ con el que se le pide al proveedor que hornee. Vive en el directorio de la
#: etapa mientras la etapa corre y se borra al acabar: es un transporte, no un
#: artefacto, y dejarlo obligaria a explicar por que hay dos mallas iguales.
TRABAJO = "_horneado.obj"

#: El lado del mapa, en texeles. Sale del perfil medido del bloque E —el hero son
#: 2048— y es parametro porque el dia que el destino mande otra cosa, la manda su
#: perfil y no una constante de aqui.
RESOLUCION_POR_DEFECTO = 2048


def suelo_de_cuantizacion_grados() -> float:
    """El angulo que mide el propio redondeo a ocho bits, para poder leer el de verdad.

    Un mapa de normales se guarda en tres canales de ocho bits: medio paso de cuantia
    por canal. Un vector unitario puede desviarse por eso hasta esa fraccion de su
    longitud, y el angulo sale de ahi:

    ```text
    (0.5 / 255) * sqrt(3) radianes -> grados
    ```

    El numero se publica **junto al medido** porque sin el, un angulo de un decimo de
    grado parece un error del horneado cuando es el fondo del formato. Y es un calculo
    y no una constante copiada: si manana el canal cambia, esto cambia con el.
    """
    import math

    return math.degrees((0.5 / 255.0) * math.sqrt(3.0))


def angulo_entre(pedidos: Any, leidos: Any) -> Any:
    """El angulo, en grados, entre el vector que se pidio y el que quedo en el mapa.

    Los dos arreglos son (n, 3) y el angulo es el de sus direcciones: la longitud no
    se juzga aqui porque el formato la redondea y ese redondeo ya esta publicado aparte
    como suelo. Se recibe por argumento y no se lee de ningun fichero, asi que se puede
    ver en rojo con dos vectores inventados.
    """
    import numpy as np

    uno = np.asarray(pedidos, dtype="float64")
    otro = np.asarray(leidos, dtype="float64")
    if uno.shape != otro.shape:
        raise ValueError(f"no se pueden comparar {uno.shape} con {otro.shape}: son la misma medida")

    def unitarios(arreglo: Any) -> Any:
        normas = np.linalg.norm(arreglo, axis=1)
        fuera = normas > 0
        salida = np.zeros_like(arreglo)
        salida[fuera] = arreglo[fuera] / normas[fuera, None]
        return salida

    coseno = (unitarios(uno) * unitarios(otro)).sum(axis=1)
    return np.degrees(np.arccos(np.clip(coseno, -1.0, 1.0)))


def sha_de_la_entrada(proyecto: pathlib.Path) -> tuple[str, str, str] | None:
    """La malla de trabajo, su hash y el atlas sobre el que se hornea, declarados.

    El atlas entra en el hash y no solo la malla: el mapa se escribe en el espacio de
    una UV concreta, asi que un atlas distinto —mismo decimado, otro corte— deja este
    mapa describiendo una superficie que ya no es la suya, y eso es exactamente lo que
    §9 llama caducar en silencio.
    """
    try:
        etapa, _ = malla_de_trabajo(proyecto)
    except ErrorDeProyecto:
        return None
    salida = salida_de(proyecto, etapa)
    if salida is None:
        return None
    atlas = salida_de(proyecto, uv.ETAPA)
    if atlas is None:
        return None
    return etapa, str(salida["sha256"]), str(atlas["sha256"])


def digest_de_la_entrada(proyecto: pathlib.Path, *, parametros: dict[str, Any]) -> str | None:
    """El hash de entrada con esos parametros, o `None` si falta algo de lo que lee."""
    entrada = sha_de_la_entrada(proyecto)
    if entrada is None:
        return None
    return hash_de_entrada(
        entradas=[entrada[1], entrada[2]],
        parametros=parametros,
        proveedor=pymeshlab.PROVEEDOR,
        version_del_proveedor=pymeshlab.version(),
    )


def _codificar(tangencial: Any) -> Any:
    """De vector unitario a color, y recortado: el formato no admite ni -0,1 ni 1,1.

    La codificacion es la del formato —`(v + 1) / 2`— y el recorte no es decorativo:
    un vertice con el marco a medias puede dar un vector de longitud algo mayor que uno
    y su color saldria fuera de rango. Se recorta y se sigue: lo que mide el angulo es
    la direccion, y la longitud esta en el suelo de cuantizacion.
    """
    import numpy as np

    return np.clip((np.asarray(tangencial, dtype="float64") + 1.0) / 2.0, 0.0, 1.0)


def _tangencial(densa: Any, marcos: dict[str, Any]) -> Any:
    """El vector de la normal medida, escrito en el marco de la malla de trabajo.

    Es la operacion que da sentido al mapa: lo que se guarda no es la normal del objeto
    —eso es lo que el proveedor escribe si se le pide su normal, y no sirve como mapa
    tangente— sino **cuanto se aparta** la superficie medida de la superficie decimada,
    medido en el marco de esta ultima.
    """
    import numpy as np

    t = marcos["tangente"]
    b = marcos["bitangente"]
    n = marcos["normal"]
    return np.stack(
        [
            (densa * t).sum(axis=1),
            (densa * b).sum(axis=1),
            (densa * n).sum(axis=1),
        ],
        axis=1,
    )


def _destino_declarado(destino: str, resolucion: int) -> dict[str, Any]:
    """El destino minimo que esta etapa necesita declarar.

    Declara **solo** lo que esta etapa promete cumplir: el lado de su mapa, que es
    potencia de dos. El resto de presupuestos —LOD, colision, densidad de texel— es del
    bloque E, y declararlos aqui en blanco seria prometer cosas que nadie ha medido.

    Y no repite el tope de solape de la etapa de UV: aquel lo declaro aquella sobre su
    atlas, y este manifiesto es de este mapa. Un `budgets` vacio es el vocabulario del
    vecino y no una promesa.
    """
    return {
        "preset": destino,
        "budgets": [],
        "textureMaxSize": resolucion,
        "texturePowerOfTwo": True,
    }


def _atlas_de_la_etapa_anterior(proyecto: pathlib.Path) -> pathlib.Path:
    """La pieza con atlas de la etapa `uv`, leida **declarada** en su informe.

    No se adivina el nombre del fichero ni se busca un `.glb` en su directorio: se lee
    lo que su informe publico como su malla, que es lo que el vecino hace y lo que el
    dia que la etapa de UV cambie de formato sigue funcionando.
    """
    salida = salida_de(proyecto, uv.ETAPA)
    if salida is None:
        raise ErrorDeProyecto(
            "no hay malla con atlas declarada por la etapa `uv`: el mapa de normales se escribe "
            "en el espacio de sus coordenadas, asi que sin ella no hay donde hornear"
        )
    return malla_de_la_etapa(proyecto, uv.ETAPA).parent / str(salida["ruta"])


def _veredicto(
    juicio: dict[str, Any] | None, motivo: str | None, directorio: pathlib.Path
) -> dict[str, Any]:
    """El juicio de R13 sobre el mapa, o su `NOT_RUN` con el motivo. Nunca un verde mudo."""
    if juicio is None:
        return {"estado": "NOT_RUN", "motivo": motivo or "sin motivo declarado"}
    informe: dict[str, Any] = juicio["informe"]
    (directorio / uv.PRODUCCION).write_text(volcar_json(informe) + "\n", encoding="utf-8")
    texturas = [
        textura for textura in informe.get("textures", []) if textura.get("artifactId") == MAPA
    ]
    return {
        "estado": "MEDIDO",
        "certificacion": juicio["certificacion"],
        "motivo": juicio["motivo"],
        "comando": juicio["comando"],
        "informe": uv.PRODUCCION,
        # Sus numeros con sus nombres: azul medio, longitud media de la normal
        # decodificada y fraccion de texeles con la z bajo el horizonte. Los tres son
        # suyos y no se recalculan aqui.
        "normal": texturas[0] if texturas else None,
    }


def _juzgar(
    asset: pathlib.Path, herramienta: pathlib.Path | None
) -> tuple[dict[str, Any] | None, str | None]:
    """Le pasa el asset al vecino. Devuelve su informe, o el motivo de no tenerlo."""
    try:
        return softsight.juicio_de_produccion(asset, herramienta=herramienta), None
    except MedicionNoDisponible as fallo:
        return None, str(fallo)


def _no_comprobado(
    veredicto: dict[str, Any], distancia: dict[str, Any], distancia_medida: dict[str, Any]
) -> list[dict[str, str]]:
    """Lo que esta etapa no miro, con su motivo. Una lista vacia es una afirmacion."""
    pendientes: list[dict[str, str]] = []
    if veredicto["estado"] != "MEDIDO":
        pendientes.append(
            {"que": "veredicto_de_produccion", "motivo": str(veredicto.get("motivo", ""))}
        )
    for nombre, medida in (
        ("distancia_de_superficie", distancia),
        ("distancia_contra_la_malla_medida", distancia_medida),
    ):
        if medida["estado"] != "MEDIDA":
            pendientes.append(
                {"que": nombre, "motivo": str(medida.get("motivo", "sin motivo declarado"))}
            )
    return pendientes


def hornear(
    proyecto: pathlib.Path,
    *,
    resolucion: int = RESOLUCION_POR_DEFECTO,
    pullpush: bool = True,
    destino: str = uv.DESTINO_POR_DEFECTO,
    herramienta: pathlib.Path | None = None,
    herramienta_de_produccion: pathlib.Path | None = None,
) -> pathlib.Path:
    """Hornea el detalle de la malla medida sobre el atlas de la malla de trabajo.

    Devuelve la ruta del informe. La malla de trabajo es la de la etapa mas avanzada
    que este hecha —hoy el decimado— y el atlas es el de la etapa `uv`: sin UV no hay
    donde hornear, y sin atlas vigente el mapa describiria una superficie que ya no es
    la suya.
    """
    import numpy as np

    ruta = pathlib.Path(proyecto)
    proyecto_abierto = abrir_proyecto(ruta)
    pymeshlab.exigir()

    etapa_de_la_malla, malla = malla_de_trabajo(ruta)
    atlas_previo = _atlas_de_la_etapa_anterior(ruta)
    entrada = sha_de_la_entrada(ruta)
    if entrada is None:
        raise ErrorDeProyecto(
            "no hay atlas del que partir: la etapa `uv` tiene que haber corrido, porque el "
            "mapa de normales se escribe en el espacio de sus coordenadas"
        )

    parametros: dict[str, Any] = {
        "resolucion": resolucion,
        "pullpush": pullpush,
        "destino": destino,
        "reposo": "vecino mas cercano sobre la malla medida",
    }
    huella = digest_de_la_entrada(ruta, parametros=parametros)
    assert huella is not None

    anterior = ultima_de(ruta, ETAPA)
    # El registro dice si la entrada cambio; **no** dice si lo que produjo sigue en su
    # sitio. Un informe borrado —o el mapa, que es lo que la etapa siguiente lee— con el
    # registro intacto daba un «ya esta hecho» que devolvia una ruta que no existe. Se
    # comprueba lo que hay en disco antes de creerse el registro.
    # El registro dice si la entrada cambio; **no** dice si lo que produjo sigue en su
    # sitio. Un informe borrado —o el mapa, que es lo que la etapa siguiente lee— con el
    # registro intacto daba un «ya esta hecho» que devolvia una ruta que no existe. Se
    # comprueba lo que hay en disco antes de creerse el registro.
    falta_lo_producido = (
        leer_informe(ruta, ETAPA) is None or not (directorio_de_etapa(ruta, ETAPA) / MAPA).is_file()
    )
    if not falta_lo_producido and not hay_que_reejecutar(anterior, hash_de_entrada=huella):
        assert anterior is not None and anterior.hash_de_salida is not None
        registrar_stage(
            ruta,
            EjecucionDeStage(
                stage=ETAPA,
                estado=EstadoDeStage.CACHED,
                hash_de_entrada=huella,
                hash_de_salida=anterior.hash_de_salida,
                determinismo=Determinismo.DETERMINISTA,
                proveedor=pymeshlab.PROVEEDOR,
                version_del_proveedor=pymeshlab.version(),
                duracion_s=0.0,
            ),
        )
        return malla_de_la_etapa(ruta, ETAPA).parent / INFORME

    empezado = time.monotonic()
    directorio = directorio_de_etapa(ruta, ETAPA)
    atlas = pymeshlab.leer_atlas(atlas_previo)
    marcos = geometria.marcos_de_uv(atlas.vertices, atlas.caras, atlas.uv)
    assert geometria.es_marco(marcos), (
        "el marco de la UV no es ortonormal: un mapa escrito en un marco torcido sale con el "
        "relieve girado y no da ningun error"
    )

    medidos, normales_de_la_medida = pymeshlab.puntos_y_normales(malla_importada(ruta))
    # La correspondencia se busca por orientacion y no solo por cercania: sobre una pared
    # delgada el vertice de enfrente esta mas cerca en linea recta y su normal apunta al
    # reves, que es lo que hace que el mapa salga con texeles mirando hacia dentro.
    vecindad = geometria.Vecindad(medidos, normales_de_la_medida)
    vecinos = vecindad.mas_cercano(atlas.vertices, referencia=marcos["normal"])
    indices = vecinos.indices
    tangencial = _tangencial(normales_de_la_medida[indices], marcos)
    codificado = _codificar(tangencial)

    # El OBJ con color por vertice es el unico transporte que el proveedor lee con UV y
    # color en el mismo fichero; esta medido y esta escrito por que en `formatos/obj.py`.
    trabajo = directorio / TRABAJO
    glb.escribir_glb(
        directorio / GLB,
        vertices=atlas.vertices,
        triangulos=atlas.caras,
        uv=atlas.uv,
        normales=marcos["normal"],
    )
    try:
        escribir_obj_coloreado(
            trabajo,
            vertices=atlas.vertices,
            caras=atlas.caras,
            uv=atlas.uv,
            colores=codificado,
        )
        horneado = pymeshlab.hornear_colores(
            trabajo, directorio / MAPA, resolucion=resolucion, pullpush=pullpush
        )
    finally:
        trabajo.unlink(missing_ok=True)

    # La comparacion se hace **en el baricentro de cada triangulo**, que es donde el texel
    # esta escrito por el propio triangulo: en una esquina de isla la regla de la arista
    # decide si su texel se cubre, y cuando no, lo que hay es el relleno. El campo pedido
    # se interpola igual que lo interpolo el rasterizador —media de las tres esquinas—,
    # asi que los dos lados de la comparacion describen el mismo punto.
    pedido = 2.0 * codificado[atlas.caras].mean(axis=1) - 1.0
    leido = 2.0 * horneado.colores_de_vuelta - 1.0
    angulos = angulo_entre(pedido, leido)
    salida_del_mapa = activo.describir_artefacto(
        directorio, MAPA, identidad=MAPA, rol="TEXTURE", usage="NORMAL"
    )
    salida_de_la_pieza = describir_malla(directorio / GLB)

    asset = activo.escribir_activo(
        directorio,
        identidad=f"{proyecto_abierto.nombre}·{etapa_de_la_malla}",
        productor=PRODUCTOR,
        version_del_productor=pymeshlab.version(),
        artefactos=[
            activo.describir_artefacto(
                directorio,
                GLB,
                identidad=IDENTIDAD_DE_LA_MAESTRA,
                rol="MASTER",
                formato="GLB",
            ),
            salida_del_mapa,
        ],
        destino=_destino_declarado(destino, resolucion),
        derivacion={
            "tool": f"videomesh/normales · pymeshlab {pymeshlab.version()}",
            "note": (
                "normal medida transferida al marco de la UV de la malla "
                f"`{etapa_de_la_malla}`; no se anadio ni un triangulo"
            ),
        },
    )

    juicio, motivo = _juzgar(asset, herramienta_de_produccion)
    veredicto = _veredicto(juicio, motivo, directorio)

    distancia = medir_distancia(malla, directorio / GLB, herramienta=herramienta)
    distancia_medida = medir_distancia(
        malla_importada(ruta), directorio / GLB, herramienta=herramienta
    )
    duracion = time.monotonic() - empezado

    registrar_stage(
        ruta,
        EjecucionDeStage(
            stage=ETAPA,
            estado=EstadoDeStage.COMPLETE,
            hash_de_entrada=huella,
            hash_de_salida=str(salida_de_la_pieza["sha256"]),
            determinismo=Determinismo.DETERMINISTA,
            proveedor=pymeshlab.PROVEEDOR,
            version_del_proveedor=pymeshlab.version(),
            duracion_s=duracion,
        ),
    )
    anotar_procedencia(
        ruta,
        Procedencia(
            etapa=ETAPA,
            artefacto=MAPA,
            # El mapa es **derivado** y no reconstruido: no anade un vertice, y sus
            # numeros son de la malla que ya estaba. Que el detalle no cupo en el
            # decimado es lo que el angulo mide.
            estado=EstadoDeProcedencia.DERIVADO,
            productor=PRODUCTOR,
            version_del_productor=pymeshlab.version(),
            package_id=None,
            fuente=str(directorio),
            ruta_del_artefacto=MAPA,
            sha256_del_artefacto=str(salida_del_mapa["sha256"]),
            maquina=None,
        ),
    )

    return escribir_informe(
        ruta,
        ETAPA,
        {
            "estado": EstadoDeStage.COMPLETE.value,
            "parametros": parametros,
            "entradas": [
                {"etapa": entrada[0], "sha256": entrada[1]},
                {"etapa": uv.ETAPA, "sha256": entrada[2]},
            ],
            "salidas": [salida_de_la_pieza, salida_del_mapa],
            "medidas": {
                "resolucion": {"lado": resolucion, "texeles": resolucion * resolucion},
                "atlas": {
                    "vertices": atlas.vertices_por_esquina,
                    "triangulos": atlas.triangulos,
                },
                "paso_de_la_malla_medida": geometria.medir_paso_de_la_malla(medidos),
                "marco": {
                    "triangulos_con_uv_reflejada": marcos["triangulos_reflejados"],
                    "triangulos_sin_uv": marcos["triangulos_sin_uv"],
                },
                "vecino_mas_cercano": {
                    "mediana": float(np.median(vecinos.distancias)),
                    "p90": float(np.percentile(vecinos.distancias, 90)),
                    "maxima": float(vecinos.distancias.max()),
                    "sin_orientacion": vecinos.sin_orientacion,
                },
                "angulo": {
                    "maximo": float(angulos.max()),
                    "medio": float(angulos.mean()),
                    "p95": float(np.percentile(angulos, 95)),
                    "baricentros": int(len(angulos)),
                    "suelo_de_cuantizacion": suelo_de_cuantizacion_grados(),
                },
                "memoria_maxima_mb": memoria_maxima_mb(),
                "distancia": distancia,
                "distancia_contra_la_malla_medida": distancia_medida,
                "duracion_s": duracion,
            },
            "purely_reconstructed": True,
            "procedencia": {
                "estado": EstadoDeProcedencia.DERIVADO.value,
                "productor": PRODUCTOR,
                "version_del_productor": pymeshlab.version(),
            },
            "veredicto_del_vecino": veredicto,
            "notas": [
                "el mapa se escribe en el marco de la UV, no en el del objeto: un mapa de "
                "objeto se lee sin error y sale con relieve absurdo, y es lo que el "
                "proveedor escribe si se le pide su propia normal",
                "el angulo se mide en el baricentro de cada triangulo, que es donde el texel "
                "esta escrito por ese triangulo, y no en sus esquinas, donde la regla de la "
                "arista decide y puede caer en el relleno",
                "y no baja del suelo de cuantizacion: el mapa son tres canales de "
                f"ocho bits ({suelo_de_cuantizacion_grados():.3f} grados de fondo)",
                "la normal medida se busca por el **vertice** mas cercano que mira hacia el "
                "mismo lado, y no por el punto mas cercano de una cara: no es un trazador de "
                "rayos, y el paso de la malla medida se publica para que la aproximacion se "
                "pueda juzgar con numeros",
                "`sin_orientacion` cuenta los vertices del atlas que no encontraron ningun "
                "vertice de la medida mirando hacia el mismo lado: son los unicos que pueden "
                "traer la normal de una pared delgada de enfrente",
                f"el relleno de texeles sin triangulo (pullpush={pullpush}) va declarado: lo "
                "que hay en ellos no es superficie de nadie",
            ],
            "no_comprobado": _no_comprobado(veredicto, distancia, distancia_medida),
        },
    )
