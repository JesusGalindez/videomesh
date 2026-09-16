"""El proxy de colisión — encargo 04, E2. Se produce **aquí**; se juzga **allí**.

El encargo subraya la frontera, y el vecino la escribe con todas las letras:
SoftSight **se niega a proponer** el proxy porque calcular un casco convexo es
modelar — en cuanto decidiera dónde va un vértice, dejaría de poder afirmar que sus
números son exactos. Producirlo es de este lado (`pymeshlab` tiene
`generate_convex_hull`); juzgar la contención es del suyo.

Lo que publica:

```text
el casco, con su cierre medido y no prometido               lo que produjo
la contencion de la maestra dentro del proxy                su auditoria
el veredicto de readiness con tope-de-holgura juzgado       lo que exige declarar
```

La contención del vecino **se niega a correr** sobre un proxy abierto: sin cierre,
«dentro» no está definido, y un número ahí parecería una respuesta. El casco es
cerrado por construcción, pero se comprueba leyendo lo escrito — prometerlo sería
publicar un `cerrado: true` que nadie midió.

**El destino declara lo que la contención exige**: `collisionSlackMax` — y
`collisionRequireConvex` si el proxy tiene que serlo. Sin holgura declarada, el
readiness del vecino deja `tope-de-holgura` hueco, y un asset sin juzgar no está
listo (R15).
"""

import json
import pathlib
import time
from typing import Any

from videomesh.adapters import pymeshlab, softsight
from videomesh.application import normales
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
    directorio_de_etapa,
    escribir_informe,
    leer_informe,
    malla_de_la_etapa,
    salida_de,
)
from videomesh.project.procedencia import anotar_procedencia
from videomesh.project.stages import registrar_stage, ultima_de
from videomesh.project.store import abrir_proyecto

__all__ = ["ETAPA", "GLB_PROXY", "construir"]

ETAPA = "colision"

PRODUCTOR = "videomesh/colision"

VERSION = "0"

#: El proxy, como GLB — el formato que el vecino lee y que este escritor sabe hacer.
GLB_PROXY = "proxy.glb"

PRODUCCION = "produccion.json"

IDENTIDAD_MAESTRA = "maestra"

IDENTIDAD_PROXY = "proxy"


def _maestra(proyecto: pathlib.Path) -> tuple[pathlib.Path, str]:
    """La pieza maestra del asset, producida por `normales` y leída de su informe.

    La contención del vecino compara el proxy contra la maestra del **asset**, y la
    maestra es la pieza con atlas y mapa — no la malla de trabajo desnuda.
    """
    salida = salida_de(proyecto, normales.ETAPA, identidad="malla")
    if salida is None:
        raise ErrorDeProyecto(
            "no hay maestra declarada por la etapa `normales`: el proxy se compara "
            "contra la pieza del asset, y sin ella no hay contra qué medir"
        )
    return (
        malla_de_la_etapa(proyecto, normales.ETAPA).parent / str(salida["ruta"]),
        str(salida["sha256"]),
    )


def _juzgar(
    asset: pathlib.Path, herramienta: pathlib.Path | None
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return softsight.juicio_de_produccion(asset, herramienta=herramienta), None
    except MedicionNoDisponible as fallo:
        return None, str(fallo)


def construir(
    proyecto: pathlib.Path,
    *,
    destino: dict[str, Any],
    herramienta: pathlib.Path | None = None,
    herramienta_de_produccion: pathlib.Path | None = None,
) -> pathlib.Path:
    """Construye el casco, lo declara como COLLISION y lo pasa por el vecino."""
    ruta = pathlib.Path(proyecto)
    proyecto_abierto = abrir_proyecto(ruta)
    pymeshlab.exigir()

    maestra, sha_maestra = _maestra(ruta)
    parametros: dict[str, Any] = {"destino": destino}
    huella = hash_de_entrada(
        entradas=[sha_maestra],
        parametros=parametros,
        proveedor=pymeshlab.PROVEEDOR,
        version_del_proveedor=pymeshlab.version(),
    )

    anterior = ultima_de(ruta, ETAPA)
    # La lección de `uv` y `normales`: lo que hay en disco se comprueba antes de
    # creerse el registro.
    falta_lo_producido = (
        leer_informe(ruta, ETAPA) is None
        or not (directorio_de_etapa(ruta, ETAPA) / GLB_PROXY).is_file()
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
    directorio.mkdir(parents=True, exist_ok=True)

    # El casco de la malla de trabajo — modelar es del productor. El cierre se mide
    # sobre lo escrito, y no se promete.
    proxy_bruto = directorio / "_casco.ply"
    try:
        medidas_del_casco = pymeshlab.casco_convexo(
            directorio.parent / "decimado" / "malla.ply", proxy_bruto
        )
        # A GLB: el formato que el vecino lee con su papel COLLISION. La geometría
        # se relee del fichero escrito — las mismas posiciones, sin segundas cifras.
        from videomesh.adapters import glb

        vertices_del_casco, caras_del_casco = pymeshlab.geometria_de(proxy_bruto)
        glb.escribir_glb(
            directorio / GLB_PROXY,
            vertices=vertices_del_casco,
            triangulos=caras_del_casco,
            uv=[(0.0, 0.0)] * len(vertices_del_casco),
        )
    finally:
        proxy_bruto.unlink(missing_ok=True)

    # La maestra viaja con el asset: la contención compara proxy contra maestra.
    # Se copia **antes** de describirla: `describir_artefacto` exige el fichero.
    import shutil

    shutil.copy2(maestra, directorio / "malla.glb")

    salida_del_proxy = activo.describir_artefacto(
        directorio, GLB_PROXY, identidad=IDENTIDAD_PROXY, rol="COLLISION", formato="GLB"
    )
    salida_de_la_maestra = activo.describir_artefacto(
        directorio, "malla.glb", identidad=IDENTIDAD_MAESTRA, rol="MASTER", formato="GLB"
    )

    asset = activo.escribir_activo(
        directorio,
        identidad=f"{proyecto_abierto.nombre}·{ETAPA}",
        productor=PRODUCTOR,
        version_del_productor=VERSION,
        artefactos=[salida_de_la_maestra, salida_del_proxy],
        destino=destino,
        derivacion={
            "tool": f"videomesh/colision · pymeshlab {pymeshlab.version()}",
            "note": "casco convexo de la malla de trabajo; la contencion la juzga el vecino",
        },
    )

    juicio, motivo = _juzgar(asset, herramienta_de_produccion)
    if juicio is None:
        veredicto: dict[str, Any] = {
            "estado": "NOT_RUN",
            "motivo": motivo or "sin motivo declarado",
        }
        contencion: dict[str, Any] | None = None
    else:
        informe: dict[str, Any] = juicio["informe"]
        (directorio / PRODUCCION).write_text(json.dumps(informe, indent=2) + "\n", encoding="utf-8")
        contencion = informe.get("collision")
        veredicto = {
            "estado": "MEDIDO",
            "certificacion": juicio["certificacion"],
            "motivo": juicio["motivo"],
            "comando": juicio["comando"],
            "informe": PRODUCCION,
            "contencion": contencion,
        }
    duracion = time.monotonic() - empezado

    bytes_del_asset = asset.read_bytes()
    import hashlib

    salida_del_asset = {
        "id": "asset",
        "ruta": activo.ACTIVO,
        "bytes": len(bytes_del_asset),
        "sha256": hashlib.sha256(bytes_del_asset).hexdigest(),
    }

    registrar_stage(
        ruta,
        EjecucionDeStage(
            stage=ETAPA,
            estado=EstadoDeStage.COMPLETE,
            hash_de_entrada=huella,
            hash_de_salida=str(salida_del_asset["sha256"]),
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
            artefacto=IDENTIDAD_PROXY,
            # El casco **añade** vértices que la superficie no tiene: es reconstruido,
            # no derivado. Decirlo bien es lo que evita que un día se lea como malla.
            estado=EstadoDeProcedencia.RECONSTRUIDO,
            productor=PRODUCTOR,
            version_del_productor=pymeshlab.version(),
            package_id=None,
            fuente=str(directorio),
            ruta_del_artefacto=GLB_PROXY,
            sha256_del_artefacto=str(salida_del_proxy["sha256"]),
            maquina=None,
        ),
    )

    return escribir_informe(
        ruta,
        ETAPA,
        {
            "estado": EstadoDeStage.COMPLETE.value,
            "parametros": parametros,
            "entradas": [{"etapa": normales.ETAPA, "sha256": sha_maestra}],
            "salidas": [salida_del_asset, salida_del_proxy],
            "medidas": {
                "proxy": {**medidas_del_casco, "fichero": GLB_PROXY},
                "duracion_s": duracion,
            },
            "purely_reconstructed": False,
            "procedencia": {
                "estado": EstadoDeProcedencia.RECONSTRUIDO.value,
                "productor": PRODUCTOR,
                "version_del_productor": pymeshlab.version(),
            },
            "veredicto_del_vecino": veredicto,
            "notas": [
                "producir el casco es de aqui y juzgar la contencion es del vecino: se "
                "niega a proponer proxies porque modelar deja de ser medir",
                "el cierre del proxy se mide sobre lo escrito y no se promete: sin "
                "cierre, la contencion del vecino se niega a correr",
                "el destino declara collisionSlackMax: sin el, el readiness deja "
                "tope-de-holgura hueco y el asset no esta listo",
            ],
            "no_comprobado": (
                [] if contencion is not None else [{"que": "contencion", "motivo": motivo or ""}]
            ),
        },
    )
