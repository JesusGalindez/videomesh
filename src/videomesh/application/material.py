"""La etapa `material` — encargo 04, D3. Viste el asset y **no lo juzga**.

R13 señala el hueco con todas las letras: el manifest de producción «todavía no
declara» los materiales — la auditoría de textura tiene su sitio y no ha tenido qué
mirar. Esta etapa lo cierra desde el lado del productor: copia la pieza con atlas y
mapa de `normales`, y declara el material que los ata en el manifiesto del vecino.

```text
que artifact pinta cada canal y a que malla aplica        lo que declara
la contradiccion del manifiesto consigo mismo             su auditoria, sin abrir imagenes
```

**No escribe su propia auditoría de materiales.** El vecino tiene `auditMaterials`:
caza — sin abrir una sola imagen — que una textura apunte a un artifact que no es
`TEXTURE`, que un material pinte una malla sin UV o un proxy de colisión, o que un
`CLAMP` conviva con UV fuera del cuadrado unidad. Reimplementar aquí cualquiera de
esos criterios daría dos criterios de qué es un material válido, y el día que
discrepen nadie sabrá cuál manda. Lo que esta etapa publica es lo que la auditoría
no puede deducir sola: que el material **declara** los mismos ficheros que produjo
la etapa anterior, con el hash de su manifiesto.

**Copia fiel, y se comprueba.** La pieza y el mapa del asset del material son los
mismos ficheros que produjo `normales`, byte a byte — el vecino comprueba los
hashes antes de mirar nada, y una copia infiel daría un asset que no es el que se
audita. No se mueve un vértice y no se repinta un texel: vestir es declarar, no
reproducir.
"""

import hashlib
import json
import pathlib
import shutil
import time
from typing import Any

from videomesh.adapters import softsight
from videomesh.application import normales
from videomesh.application.trabajo import malla_de_trabajo
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
)
from videomesh.project.procedencia import anotar_procedencia
from videomesh.project.stages import registrar_stage, ultima_de
from videomesh.project.store import abrir_proyecto

__all__ = ["ETAPA", "GLB", "MAPA", "PRESET_POR_DEFECTO", "digest_de_la_entrada", "vestir"]

ETAPA = "material"

PRODUCTOR = "videomesh/material"

VERSION = "0"

#: La pieza y el mapa, con el nombre con el que los produce `normales`. La copia es
#: fiel, así que el nombre viaja: un material que declara `normales.png` mientras el
#: fichero se llama de otra cosa sería la clase de contradicción que el propio
#: vecino caza.
GLB = normales.GLB
MAPA = normales.MAPA

#: El preset que se declara si nadie dice otro. Los perfiles con presupuestos son
#: del bloque E; este es el nombre para citar el destino del asset vestido.
PRESET_POR_DEFECTO = "material-de-trabajo"

#: El informe del vecino, junto al asset que juzgó. Mismo nombre que en las etapas
#: `uv` y `normales`, porque es el mismo informe de producción.
PRODUCCION = "produccion.json"


def _salidas_de_normales(proyecto: pathlib.Path) -> dict[str, dict[str, Any]]:
    """Los artefactos que `normales` publicó, leídos **declarados** en su informe.

    No se adivina ni se rehashea: lo que esta etapa declara es lo que aquella
    publicó, y su informe es la fuente.
    """
    informe = leer_informe(proyecto, normales.ETAPA)
    if informe is None:
        raise ErrorDeProyecto(
            "no hay etapa `normales` de la que partir: el material viste la pieza con "
            "atlas y mapa que aquella produce, y sin ella no hay nada que vestir"
        )
    # Por el nombre del fichero y no por `id`: la pieza se declara con la identidad
    # generica ("malla") y lo que la nombra de verdad es el fichero que produce. Y
    # con los dos vocabularios: las mallas van con `ruta` y lo descrito con
    # `describir_artefacto` va con `path`, que es el campo del asset del vecino.
    salidas = {}
    for salida in informe.get("salidas", []):
        nombre = salida.get("ruta") or salida.get("path")
        if nombre is not None:
            salidas[str(nombre)] = salida
    for nombre in (normales.GLB, normales.MAPA):
        if nombre not in salidas:
            raise ErrorDeProyecto(
                f"la etapa `normales` no declara {nombre!r} entre sus salidas: el "
                "material viste lo que aquella publicó, y sin él no hay material que "
                "declarar"
            )
    return salidas


def sha_de_la_entrada(proyecto: pathlib.Path) -> dict[str, str] | None:
    """El hash de la pieza y del mapa, leídos del informe de `normales`."""
    try:
        salidas = _salidas_de_normales(proyecto)
    except ErrorDeProyecto:
        return None
    return {
        "pieza": str(salidas[normales.GLB]["sha256"]),
        "mapa": str(salidas[normales.MAPA]["sha256"]),
    }


def digest_de_la_entrada(proyecto: pathlib.Path, *, parametros: dict[str, Any]) -> str | None:
    """El hash de entrada con esos parámetros, o `None` si falta la etapa anterior."""
    hashes = sha_de_la_entrada(proyecto)
    if hashes is None:
        return None
    return hash_de_entrada(
        entradas=[hashes["pieza"], hashes["mapa"]],
        parametros=parametros,
        proveedor=PRODUCTOR,
        version_del_proveedor=VERSION,
    )


def _material_declarado() -> dict[str, Any]:
    """El material que esta etapa declara, en el vocabulario del vecino.

    Una sola pieza, un solo material: `appliesTo` apunta a la identidad del artifact
    maestra — no al fichero — y el canal `normal` al id del mapa. `wrap` es REPEAT
    porque el atlas vive dentro del cuadrado unidad y el empaquetado no tiene por
    qué pelearse con un CLAMP; `alphaMode` OPAQUE porque los texeles son de la
    superficie y no hay alfa que mezclar.
    """
    return {
        "id": "material-de-la-superficie",
        "appliesTo": ["maestra"],
        "textures": {"normal": normales.MAPA},
        "wrap": "REPEAT",
        "alphaMode": "OPAQUE",
    }


def _juzgar(
    asset: pathlib.Path, herramienta: pathlib.Path | None
) -> tuple[dict[str, Any] | None, str | None]:
    """Le pasa el asset al vecino. Devuelve su informe, o el motivo de no tenerlo."""
    try:
        return softsight.juicio_de_produccion(asset, herramienta=herramienta), None
    except MedicionNoDisponible as fallo:
        return None, str(fallo)


def _veredicto(
    juicio: dict[str, Any] | None,
    motivo: str | None,
    directorio: pathlib.Path,
    materiales_declarados: int,
) -> dict[str, Any]:
    """El veredicto del vecino —con lo del material—, o su `NOT_RUN` con el motivo."""
    if juicio is None:
        return {"estado": "NOT_RUN", "motivo": motivo or "sin motivo declarado"}
    informe: dict[str, Any] = juicio["informe"]
    (directorio / PRODUCCION).write_text(json.dumps(informe, indent=2) + "\n", encoding="utf-8")
    return {
        "estado": "MEDIDO",
        "certificacion": juicio["certificacion"],
        "motivo": juicio["motivo"],
        "comando": juicio["comando"],
        "informe": PRODUCCION,
        # Lo que su `auditMaterials` cazó sobre lo que declara esta etapa. Una lista
        # vacía **es** la condición del PASS, y se publica porque no auditar nada y
        # no tener contradicciones se leen igual sin este número al lado.
        "materialIssues": informe.get("materialIssues", []),
        # Lo que el vecino leyó: los materiales del asset sellado que se le pasó. Su
        # informe no lo devuelve, y el manifiesto es la entrada de su auditoría.
        "materiales_declarados": materiales_declarados,
    }


def _no_comprobado(veredicto: dict[str, Any]) -> list[dict[str, str]]:
    """Lo que esta etapa no miró, con su motivo. Una lista vacía es una afirmación."""
    pendientes: list[dict[str, str]] = []
    if veredicto["estado"] != "MEDIDO":
        pendientes.append(
            {"que": "veredicto_de_produccion", "motivo": str(veredicto.get("motivo", ""))}
        )
    return pendientes


def vestir(
    proyecto: pathlib.Path,
    *,
    destino: str = PRESET_POR_DEFECTO,
    herramienta_de_produccion: pathlib.Path | None = None,
) -> pathlib.Path:
    """Viste la pieza de `normales` con su material, y devuelve su informe.

    El asset queda con los dos artefactos y el material que los ata: la auditoría de
    textura del vecino tiene así un material que auditar, y su veredicto —con
    `materialIssues` incluido— es el que cierra la etapa.
    """
    ruta = pathlib.Path(proyecto)
    proyecto_abierto = abrir_proyecto(ruta)

    malla_de_trabajo(ruta)  # exige que la cadena tenga malla de trabajo
    # Sin informe del que partir, el error de `_salidas_de_normales` es el que
    # llega: no se traga aquí para cambiarlo por un assert mudo.
    salidas = _salidas_de_normales(ruta)
    hashes = {
        "pieza": str(salidas[normales.GLB]["sha256"]),
        "mapa": str(salidas[normales.MAPA]["sha256"]),
    }

    parametros: dict[str, Any] = {"destino": destino}
    huella = digest_de_la_entrada(ruta, parametros=parametros)
    assert huella is not None

    anterior = ultima_de(ruta, ETAPA)
    # El registro dice si la entrada cambió; **no** dice si lo que produjo sigue en
    # su sitio. La misma lección de `uv` y `normales`: lo que hay en disco se
    # comprueba antes de creerse el registro.
    falta_lo_producido = leer_informe(ruta, ETAPA) is None or any(
        not (directorio_de_etapa(ruta, ETAPA) / nombre).is_file() for nombre in (GLB, MAPA)
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
                proveedor=PRODUCTOR,
                version_del_proveedor=VERSION,
                duracion_s=0.0,
            ),
        )
        return malla_de_la_etapa(ruta, ETAPA).parent / INFORME

    empezado = time.monotonic()
    directorio = directorio_de_etapa(ruta, ETAPA)
    # Aqui no hay escritor de malla que cree el directorio de paso: la primera
    # operacion es la copia, y la copia no crea directorios.
    directorio.mkdir(parents=True, exist_ok=True)
    # Copia fiel de lo que produjo `normales`: byte a byte, y el hash que declara el
    # asset es el de lo que hay en el disco de este directorio.
    for nombre in (GLB, MAPA):
        shutil.copy2(proyecto / "etapas" / normales.ETAPA / nombre, directorio / nombre)

    material = _material_declarado()
    asset = activo.escribir_activo(
        directorio,
        identidad=f"{proyecto_abierto.nombre}·{normales.ETAPA}",
        productor=PRODUCTOR,
        version_del_productor=VERSION,
        artefactos=[
            activo.describir_artefacto(
                directorio, GLB, identidad="maestra", rol="MASTER", formato="GLB"
            ),
            activo.describir_artefacto(
                directorio, MAPA, identidad=MAPA, rol="TEXTURE", usage="NORMAL"
            ),
        ],
        destino={"preset": destino, "budgets": []},
        materiales=[material],
        derivacion={
            "tool": "videomesh/material",
            "note": (
                "el material que ata la pieza y el mapa de la etapa `normales`; no se "
                "mueve un vertice ni se repinta un texel"
            ),
        },
    )

    juicio, motivo = _juzgar(asset, herramienta_de_produccion)
    # Lo que el vecino acaba de leer: el manifiesto que se le pasó, sellado.
    cuantos_materiales = len(json.loads(asset.read_text(encoding="utf-8")).get("materials") or [])
    veredicto = _veredicto(juicio, motivo, directorio, cuantos_materiales)
    duracion = time.monotonic() - empezado

    bytes_del_asset = asset.read_bytes()
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
            proveedor=PRODUCTOR,
            version_del_proveedor=VERSION,
            duracion_s=duracion,
        ),
    )
    anotar_procedencia(
        ruta,
        Procedencia(
            etapa=ETAPA,
            artefacto=activo.ACTIVO,
            # Vestir es **derivar**: los dos ficheros ya estaban, y lo que añade la
            # etapa es el material que los ata en el manifiesto del vecino.
            estado=EstadoDeProcedencia.DERIVADO,
            productor=PRODUCTOR,
            version_del_productor=VERSION,
            package_id=None,
            fuente=str(directorio),
            ruta_del_artefacto=activo.ACTIVO,
            sha256_del_artefacto=str(salida_del_asset["sha256"]),
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
                {"etapa": normales.ETAPA, "sha256": hashes["pieza"]},
                {"etapa": normales.ETAPA, "sha256": hashes["mapa"]},
            ],
            "salidas": [salida_del_asset],
            "medidas": {
                "material": material,
                "artefactos_vestidos": [GLB, MAPA],
                "hashes_de_lo_que_produjo_normales": hashes,
                "duracion_s": duracion,
            },
            "purely_reconstructed": True,
            "procedencia": {
                "estado": EstadoDeProcedencia.DERIVADO.value,
                "productor": PRODUCTOR,
                "version_del_proveedor": VERSION,
            },
            "veredicto_del_vecino": veredicto,
            "notas": [
                "vestir es declarar, no reproducir: los dos artefactos son los ficheros "
                "de `normales`, byte a byte, y el material es lo que los ata",
                "la auditoria del material la hace el vecino con `auditMaterials`, sin "
                "abrir imagenes: aqui no hay un segundo criterio de material valido",
            ],
            "no_comprobado": _no_comprobado(veredicto),
        },
    )
