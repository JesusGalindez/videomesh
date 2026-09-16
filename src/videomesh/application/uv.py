"""La etapa `uv` — encargo 04, C2. Corta y empaqueta el atlas, y **no lo juzga**.

Lo que publica:

```text
islas, empaquetado y los vertices que las costuras anaden      lo que produjo
las dos distancias de superficie, contra su entrada y contra
la malla medida                                                el criterio de cierre
el veredicto del vecino sobre las UV                           su auditoria
```

Lo que **no** publica es ninguna medida de validez de las UV: ni solape, ni area
nula, ni densidad de texel. Eso lo mide `auditUvs` de SoftSight sobre el GLB y sale
en su informe de produccion, y el caso rojo de esta etapa es exactamente que un atlas
con UV solapadas lo rechace **el vecino**. Dos criterios de que es una UV valida
acabarian discrepando, y el dia que lo hagan nadie sabra cual manda.

El GLB existe por eso y no por gusto de formato: un PLY no admite coordenadas de
textura, y sin un fichero que las lleve la auditoria no tiene nada que mirar. Es el
minimo —una pieza, `POSITION` y `TEXCOORD_0`, sin extensiones— y el empaquetado final
con KTX2 es del bloque E.

**Partir no es mover.** Las costuras obligan a duplicar vertices, asi que la malla sale
con mas vertices que entro; sus posiciones son las mismas y la superficie no cambia.
Por eso se publican las dos cosas juntas: cuantos vertices anadio el corte, y la
distancia de superficie en las dos direcciones —que es cero, y lo dice un numero y no
una promesa—.
"""

import pathlib
import time
from typing import Any

from videomesh.adapters import glb, pymeshlab, softsight, xatlas
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
from videomesh.project import activo
from videomesh.project.informe import (
    INFORME,
    describir_malla,
    directorio_de_etapa,
    escribir_informe,
    malla_de_la_etapa,
    salida_de,
)
from videomesh.project.procedencia import anotar_procedencia
from videomesh.project.stages import registrar_stage, ultima_de
from videomesh.project.store import abrir_proyecto

__all__ = [
    "DESTINO_POR_DEFECTO",
    "ETAPA",
    "GLB",
    "PRODUCCION",
    "SOLAPE_MAXIMO_POR_DEFECTO",
    "cortar_y_empaquetar",
    "digest_de_la_entrada",
    "sha_de_la_entrada",
]

ETAPA = "uv"

PRODUCTOR = "videomesh/uv"

#: El nombre del GLB de la etapa, en un solo sitio: la auditoria del vecino lo busca
#: por el, desde el manifiesto.
GLB = "malla.glb"

#: El informe del vecino, tal cual, junto al asset que juzgo.
PRODUCCION = "produccion.json"

#: El destino que se declara si nadie dice otro. Es un nombre para citarlo, y no un
#: perfil: los perfiles medidos —hero y fondo— son del bloque E.
DESTINO_POR_DEFECTO = "uv-de-trabajo"

#: El tope de solape que esta etapa declara cumplir, como fraccion del area de las
#: islas. Un atlas que pisa dos veces el mismo texel pinta una vez y ensena la otra, y
#: que eso se vea en la puerta es de lo que va este bloque.
#:
#: **No es cero, y el motivo esta medido.** La auditoria del vecino mide el solape
#: contra la union de una rejilla de 256 celdas, asi que el suelo de la medida no es
#: cero y ademas **no baja con el margen**: medido el 2026-09-16 sobre un cubo de seis
#: islas, el mismo atlas limpio da 0,000 % con margen 0, 0,168 % con margen 2, 0,488 %
#: con margen 4, 0,000 % con margen 8 y 0,039 % con margen 16 — la cuantizacion de la
#: rejilla contra el empaquetado, no una costura. Sobre la malla de 2.915 triangulos de
#: Colab, 151 islas, margen 2: 0,000 %.
#:
#: Un tope de cero suspenderia el atlas de un cubo que no tiene ni un triangulo
#: encima de otro, y por eso se declara una tolerancia que separa los dos mundos: el
#: peor caso medido de un atlas limpio es 0,488 %, y un solape de verdad —dos
#: triangulos sobre las mismas UV— mide mas del 90 %. El uno por ciento deja el suelo a
#: la mitad y el solape real a noventa veces. **El tope del destino lo declara el
#: destino**: el bloque E lo cambia por el que traigan sus perfiles medidos.
SOLAPE_MAXIMO_POR_DEFECTO = 0.01


def sha_de_la_entrada(proyecto: pathlib.Path) -> tuple[str, str] | None:
    """La etapa que produjo la malla de trabajo y el hash que declaro de ella.

    Se lee **declarado** en el informe de esa etapa y no se rehashea el fichero: el
    hash ya lo calculo quien lo escribio, y volver a calcularlo daria dos cifras de lo
    mismo — la misma razon que en `decimado.sha_de_la_entrada`.
    """
    try:
        etapa, _ = malla_de_trabajo(proyecto)
    except ErrorDeProyecto:
        return None
    salida = salida_de(proyecto, etapa)
    if salida is None:
        return None
    return etapa, str(salida["sha256"])


def digest_de_la_entrada(proyecto: pathlib.Path, *, parametros: dict[str, Any]) -> str | None:
    """El hash de entrada con esos parametros, o `None` si no hay malla de trabajo."""
    entrada = sha_de_la_entrada(proyecto)
    if entrada is None:
        return None
    return hash_de_entrada(
        entradas=[entrada[1]],
        parametros=parametros,
        proveedor=xatlas.PROVEEDOR,
        version_del_proveedor=xatlas.version(),
    )


def _destino_declarado(destino: str, solape_maximo: float) -> dict[str, Any]:
    """El destino minimo que esta etapa necesita declarar.

    Declara **solo** lo que promete cumplir: el solape, con el nombre y el tope que su
    auditoria entiende. Los presupuestos de LOD, textura y colision son del bloque E, y
    declararlos aqui en blanco seria prometer cosas que nadie ha medido.

    `budgets` va vacio a proposito: esa lista es el vocabulario de presupuestos del
    vecino, y un nombre que su evaluador no conoce no aprueba — deja el veredicto en
    «no disponible», que es peor que no declararlo.
    """
    if solape_maximo < 0:
        raise ValueError(
            f"el tope de solape es una fraccion de area y no puede ser negativo: {solape_maximo}"
        )
    return {"preset": destino, "budgets": [], "uvOverlapMax": solape_maximo}


def _maestra(informe: dict[str, Any]) -> dict[str, Any] | None:
    """La medida de la malla maestra dentro del informe del vecino, tal cual.

    Se copian **sus** numeros con **sus** nombres. No se renombran ni se recalculan:
    son su auditoria, y una segunda version de sus cifras acabaria discrepando.
    """
    for medida in informe.get("measurements", []):
        if medida.get("role") == "MASTER":
            devuelta: dict[str, Any] = medida
            return devuelta
    return None


def _veredicto(
    juicio: dict[str, Any] | None, motivo: str | None, directorio: pathlib.Path
) -> dict[str, Any]:
    """El veredicto del vecino, o su `NOT_RUN` con el motivo. Nunca un verde por omision."""
    if juicio is None:
        return {"estado": "NOT_RUN", "motivo": motivo or "sin motivo declarado"}
    informe: dict[str, Any] = juicio["informe"]
    (directorio / PRODUCCION).write_text(volcar_json(informe) + "\n", encoding="utf-8")
    maestra = _maestra(informe)
    veredicto: dict[str, Any] = {
        "estado": "MEDIDO",
        "certificacion": juicio["certificacion"],
        "motivo": juicio["motivo"],
        "comando": juicio["comando"],
        # El informe entero, al lado del asset que juzgo: un veredicto citado sin su
        # informe obliga a repetir la auditoria para comprobar que decia.
        "informe": PRODUCCION,
        "maestra": None,
    }
    if maestra is not None:
        veredicto["maestra"] = {
            "triangulos": maestra.get("triangles"),
            "uv": maestra.get("uv"),
            "veredictos": maestra.get("uvVerdicts"),
        }
    return veredicto


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
    """Lo que esta etapa **no** miro, con su motivo. Una lista vacia es una afirmacion."""
    pendientes = []
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


def cortar_y_empaquetar(
    proyecto: pathlib.Path,
    *,
    margen: int = xatlas.MARGEN_POR_DEFECTO,
    iteraciones: int = xatlas.ITERACIONES_POR_DEFECTO,
    destino: str = DESTINO_POR_DEFECTO,
    solape_maximo: float = SOLAPE_MAXIMO_POR_DEFECTO,
    herramienta: pathlib.Path | None = None,
    herramienta_de_produccion: pathlib.Path | None = None,
) -> pathlib.Path:
    """Corta y empaqueta el atlas de la malla de trabajo. Devuelve su informe.

    La distancia se mide **contra la malla medida**, y no solo contra su entrada: es el
    freno del bucle (F2) y el unico numero que dice si el asset sigue siendo el objeto.
    """
    ruta = pathlib.Path(proyecto)
    proyecto_abierto = abrir_proyecto(ruta)
    xatlas.exigir()

    etapa_de_la_malla, malla = malla_de_trabajo(ruta)
    entrada = sha_de_la_entrada(ruta)
    assert entrada is not None  # hay malla de trabajo: `malla_de_trabajo` acaba de leerla

    parametros: dict[str, Any] = {
        "margen": margen,
        "iteraciones": iteraciones,
        "destino": destino,
        "solape_maximo": solape_maximo,
    }
    huella = digest_de_la_entrada(ruta, parametros=parametros)
    assert huella is not None

    anterior = ultima_de(ruta, ETAPA)
    if not hay_que_reejecutar(anterior, hash_de_entrada=huella):
        assert anterior is not None and anterior.hash_de_salida is not None
        registrar_stage(
            ruta,
            EjecucionDeStage(
                stage=ETAPA,
                estado=EstadoDeStage.CACHED,
                hash_de_entrada=huella,
                hash_de_salida=anterior.hash_de_salida,
                determinismo=Determinismo.DETERMINISTA,
                proveedor=xatlas.PROVEEDOR,
                version_del_proveedor=xatlas.version(),
                duracion_s=0.0,
            ),
        )
        return malla_de_la_etapa(ruta, ETAPA).parent / INFORME

    empezado = time.monotonic()
    directorio = directorio_de_etapa(ruta, ETAPA)
    # Los vertices de antes los mide el proveedor sobre el fichero, y no se copian del
    # informe de la etapa anterior: la cuenta que publica este informe es la de la malla
    # que se corto de verdad.
    vertices_de_entrada = pymeshlab.medir(malla).vertices
    atlas = xatlas.cortar_y_empaquetar(malla, margen=margen, iteraciones=iteraciones)
    glb.escribir_glb(
        directorio / GLB,
        vertices=atlas.vertices,
        triangulos=atlas.triangulos,
        uv=atlas.uv,
    )
    salida = describir_malla(directorio / GLB)

    # El manifiesto de produccion, con la maestra y el tope que esta etapa declara. Es
    # lo que el vecino lee: sin manifiesto sellado su informe no mira nada, y una etapa
    # sin juez esta a medias.
    asset = activo.escribir_activo(
        directorio,
        # La identidad sale del nombre **declarado** del proyecto y de la etapa que
        # produjo la malla, nunca del nombre del directorio: mover una carpeta no
        # cambia lo que hay dentro.
        identidad=f"{proyecto_abierto.nombre}·{etapa_de_la_malla}",
        productor=PRODUCTOR,
        version_del_productor=xatlas.version(),
        artefactos=[
            activo.describir_artefacto(
                directorio, GLB, identidad="maestra", rol="MASTER", formato="GLB"
            )
        ],
        destino=_destino_declarado(destino, solape_maximo),
        derivacion={
            "tool": f"videomesh/uv · xatlas {xatlas.version()}",
            "note": (
                "atlas de la malla de trabajo; la geometria es la de la etapa "
                f"`{etapa_de_la_malla}`, sin un vertice movido"
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
            hash_de_salida=str(salida["sha256"]),
            determinismo=Determinismo.DETERMINISTA,
            proveedor=xatlas.PROVEEDOR,
            version_del_proveedor=xatlas.version(),
            duracion_s=duracion,
        ),
    )
    anotar_procedencia(
        ruta,
        Procedencia(
            etapa=ETAPA,
            artefacto="maestra",
            # Partir los vertices por las costuras es **derivar**, no simplificar: no se
            # tiro un triangulo y no se movio una posicion.
            estado=EstadoDeProcedencia.DERIVADO,
            productor=PRODUCTOR,
            version_del_productor=xatlas.version(),
            package_id=None,
            fuente=str(directorio),
            ruta_del_artefacto=GLB,
            sha256_del_artefacto=str(salida["sha256"]),
            maquina=None,
        ),
    )

    return escribir_informe(
        ruta,
        ETAPA,
        {
            "estado": EstadoDeStage.COMPLETE.value,
            "parametros": parametros,
            "entradas": [{"etapa": entrada[0], "sha256": entrada[1]}],
            "salidas": [salida, describir_malla(asset, identidad="activo")],
            "medidas": {
                "islas": atlas.islas,
                "empaquetado": {"ancho": atlas.empaquetado[0], "alto": atlas.empaquetado[1]},
                "vertices_antes": vertices_de_entrada,
                "vertices_despues": int(len(atlas.vertices)),
                "vertices_anadidos_por_las_costuras": int(len(atlas.vertices))
                - vertices_de_entrada,
                "triangulos": int(len(atlas.triangulos)),
                "memoria_maxima_mb": memoria_maxima_mb(),
                "distancia": distancia,
                "distancia_contra_la_malla_medida": distancia_medida,
                "duracion_s": duracion,
            },
            "purely_reconstructed": True,
            "procedencia": {
                "estado": EstadoDeProcedencia.DERIVADO.value,
                "productor": PRODUCTOR,
                "version_del_productor": xatlas.version(),
            },
            "veredicto_del_vecino": veredicto,
            # Dos numeros que se leen mal sin la nota al lado, y las dos notas estan
            # donde estan los numeros.
            "notas": [
                "el solape que se declara es una tolerancia, no un cero ideal: se mide "
                f"sobre una rejilla y su suelo no es cero (tope declarado "
                f"{parametros['solape_maximo']})",
                "el GLB escribe las posiciones en coma flotante de 32 bits, asi que la "
                "distancia contra su entrada tiene el suelo del formato y no el del diff: "
                "medido el 2026-09-16 sobre la malla de 2.915 triangulos, falta 1,98e-12 "
                "con suelo del diff 1,03e-14 — no se movio un vertice, se redondeo al "
                "escribirse",
            ],
            "no_comprobado": _no_comprobado(veredicto, distancia, distancia_medida),
        },
    )
