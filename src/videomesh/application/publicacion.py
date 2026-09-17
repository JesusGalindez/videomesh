"""La etapa `publicacion` — encargo 04, E4. Sella el paquete y **publica el veredicto**.

Es lo único de la cadena que no produce una pieza más: produce el veredicto. Junta lo
que las etapas anteriores publicaron, lo sella con el destino declarado, y lo pasa por
la QA de SoftSight. Sale `PRODUCTION_READY` o sale `UNKNOWN` con la lista de lo que
falta — y esa lista se copia de su informe, check a check, con el motivo que él escribió.

```text
el paquete sellado, con los hashes leidos del disco      lo que se publica
el veredicto del vecino sobre ese paquete                el criterio de cierre
el informe del validador de Khronos                      sin el no hay aprobacion (R15)
la variante de reparto, declarada NOT_RUN                lo que no se puede auditar
```

**Tres cosas que no son obvias y están decididas aquí.**

1. **El manifiesto se escribe el último**, después de copiar cada artefacto, y sus
   `bytes` y `sha256` se leen del fichero ya escrito. Es el orden del sellado (V5) y no
   una preferencia: un manifiesto que declara lo que alguien creía pesar es una mentira
   que su propia puerta caza al abrir el paquete.
2. **La variante de reparto no se declara como artifact.** Su cargador rechaza
   `KHR_texture_basisu`, y un artifact que no se puede abrir no le da un `NOT_RUN`: le
   revienta el informe entero — medido: sale 20 y sin informe. Así que el manifiesto
   declara lo que su lector puede leer, el paquete lleva las dos, y el `NOT_RUN` de la
   de reparto se publica aquí, en `no_comprobado`, que es donde se dice lo que no se
   miró.
3. **El validador de Khronos se ejecuta**, y su informe viaja al vecino por
   `--external`. Sin él su `readiness` deja `validador-externo` en `NINGUN_VALIDADOR_
   EXTERNO_APORTADO` y el veredicto es `UNKNOWN`: decir «es un GLB válido» sin que
   nadie lo haya validado es afirmarlo sin haberlo comprobado.

El paquete se escribe en un directorio temporal y se renombra al acabar: mientras se
escribe no hay nada que nadie pueda leer como un paquete. El destino anterior se retira
**después** de que el nuevo esté entero — una etapa que no se puede volver a ejecutar
tras cambiar algo de arriba dejaría la cadena atascada, y volver a publicar es una
ejecución nueva, no un paquete pisado a medias.
"""

import hashlib
import json
import pathlib
import shutil
import tempfile
import time
from typing import Any

from videomesh.adapters import gltf_validator, softsight
from videomesh.application import glb_final, normales, perfiles
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
    salida_de,
)
from videomesh.project.procedencia import anotar_procedencia
from videomesh.project.stages import registrar_stage, ultima_de
from videomesh.project.store import abrir_proyecto

__all__ = [
    "ETAPA",
    "PAQUETES",
    "informe_del_vecino",
    "publicar",
]

ETAPA = "publicacion"

PRODUCTOR = "videomesh/publicacion"

VERSION = "0"

#: Dónde viven los paquetes publicados dentro del proyecto. El nombre del destino es el
#: de la carpeta: publicar el mismo asset para dos destinos da dos paquetes, y ninguno
#: pisa al otro.
PAQUETES = "publicacion"

#: El informe del vecino, junto al asset que juzgó. El mismo nombre que en `uv`,
#: `normales` y `material`, porque es el mismo informe de producción.
PRODUCCION = "produccion.json"

#: El informe del validador de Khronos, y el de la variante de reparto. Viajan con el
#: paquete: son la prueba de lo que se dijo de él.
VALIDACION = "validacion-externa.json"
VALIDACION_DE_REPARTO = "validacion-externa-reparto.json"


def _piezas_del_paquete(destino: dict[str, Any]) -> tuple[str, ...]:
    """Qué piezas se publican: lo que el destino declara, o lo mínimo de una entrega."""
    return perfiles.piezas_de_reparto(str(destino.get("preset", "")))


def _las_del_glb(proyecto: pathlib.Path) -> dict[str, dict[str, Any]]:
    """La maestra, su mapa y la variante de reparto, **leídas del informe de `glb`**.

    No se rehashean los ficheros ni se adivinan sus nombres: lo que la publicación
    declara es lo que aquella etapa publicó, y su informe es la fuente. Lo que sí se
    comprueba es que los tres estén donde dicen — un informe sin su fichero es un
    registro, no un artefacto.
    """
    salidas: dict[str, dict[str, Any]] = {}
    for clave, identidad in (
        ("maestra", glb_final.IDENTIDAD_DE_LA_MAESTRA),
        ("mapa", normales.MAPA),
        ("reparto", glb_final.GLB_KTX2),
    ):
        salida = salida_de(proyecto, glb_final.ETAPA, identidad=identidad)
        if salida is None:
            raise ErrorDeProyecto(
                f"no hay etapa `{glb_final.ETAPA}` de la que partir: la publicacion sella el "
                "asset que aquella empaqueta, y sin el no hay nada que publicar"
            )
        salidas[clave] = salida
    return salidas


def digest_de_la_entrada(proyecto: pathlib.Path, *, parametros: dict[str, Any]) -> str | None:
    """El hash de entrada de la publicación con esos parámetros, o `None` si falta `glb`."""
    try:
        entradas = _las_del_glb(proyecto)
    except ErrorDeProyecto:
        return None
    return hash_de_entrada(
        entradas=[str(entradas["maestra"]["sha256"]), str(entradas["mapa"]["sha256"])],
        parametros=parametros,
        proveedor=PRODUCTOR,
        version_del_proveedor=VERSION,
    )


def informe_del_vecino(proyecto: pathlib.Path) -> dict[str, Any] | None:
    """El informe de producción que la publicación guardó, si lo hay."""
    ruta = directorio_de_etapa(pathlib.Path(proyecto), ETAPA) / PRODUCCION
    if not ruta.is_file():
        return None
    documento: dict[str, Any] = json.loads(ruta.read_text(encoding="utf-8"))
    return documento


def _lo_que_falta(informe: dict[str, Any]) -> list[dict[str, str]]:
    """La lista de lo que impide la aprobación, tal y como la escribió el vecino.

    Se copian sus estados y sus motivos y no se traducen: un `FAIL` y un `NOT_RUN` son
    cosas distintas —una dice que algo está mal, la otra que no se sabe— y fundirlas en
    una lista de «problemas» perdería la única distinción que hace falta para decidir
    qué hacer después.
    """
    readiness = informe.get("readiness") or {}
    falta: list[dict[str, str]] = []
    for comprobacion in readiness.get("checks") or []:
        if comprobacion.get("state") not in ("FAIL", "NOT_RUN"):
            continue
        falta.append(
            {
                "id": str(comprobacion.get("id")),
                "estado": str(comprobacion.get("state")),
                "motivo": str(comprobacion.get("reason") or ""),
            }
        )
    return falta


def _copiar_la_maestra(directorio: pathlib.Path, maestra: pathlib.Path, mapa: pathlib.Path) -> None:
    """Copia la maestra y su mapa al paquete, con sus nombres.

    La copia es fiel y **con el mismo nombre**: el material declara el mapa por su nombre
    de fichero, y renombrarlo aquí sería la clase de contradicción que el vecino caza sin
    abrir nada.
    """
    shutil.copy2(maestra, directorio / glb_final.GLB_SIN_KTX2)
    shutil.copy2(mapa, directorio / normales.MAPA)


def _swap(provisional: pathlib.Path, destino: pathlib.Path) -> None:
    """Pone el paquete nuevo en su sitio, y retira el anterior **después**.

    No es el `rename` del sellado, que exige que el destino no exista: aquí el destino
    es el directorio de salida de esta etapa, y una etapa que solo se puede publicar una
    vez dejaría la cadena atascada en cuanto algo de arriba cambiara. Lo que se conserva
    del sellado es lo que importa: mientras se escribe, el paquete no está.
    """
    if destino.exists():
        shutil.rmtree(destino)
    provisional.rename(destino)


def publicar(
    proyecto: pathlib.Path,
    *,
    destino: dict[str, Any],
    herramienta: pathlib.Path | None = None,
    herramienta_de_produccion: pathlib.Path | None = None,
) -> pathlib.Path:
    """Publica el paquete de producción y devuelve su informe.

    El destino manda y entra en el hash de entrada: publicar el mismo asset para dos
    destinos da dos paquetes, y cambiar el destino caduca la etapa.
    """
    ruta = pathlib.Path(proyecto)
    # Se abre para exigir que sea un proyecto: publicar sobre un directorio que no lo
    # es escribiria un paquete donde nadie lo va a buscar.
    abrir_proyecto(ruta)

    entradas = _las_del_glb(ruta)
    piezas = _piezas_del_paquete(destino)
    nombre = str(destino.get("preset", "asset"))
    parametros: dict[str, Any] = {
        "destino": json.loads(json.dumps(destino)),
        "piezas": list(piezas),
    }
    huella = hash_de_entrada(
        entradas=[str(entradas["maestra"]["sha256"]), str(entradas["mapa"]["sha256"])],
        parametros=parametros,
        proveedor=PRODUCTOR,
        version_del_proveedor=VERSION,
    )

    paquete = ruta / PAQUETES / nombre
    anterior = ultima_de(ruta, ETAPA)
    falta_lo_producido = (
        leer_informe(ruta, ETAPA) is None or not (paquete / activo.ACTIVO).is_file()
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
        return directorio_de_etapa(ruta, ETAPA) / INFORME

    empezado = time.monotonic()
    directorio = directorio_de_etapa(ruta, ETAPA)
    directorio.mkdir(parents=True, exist_ok=True)
    fuente = ruta / "etapas" / glb_final.ETAPA
    maestra = fuente / glb_final.GLB_SIN_KTX2
    mapa = fuente / normales.MAPA
    reparto = fuente / glb_final.GLB_KTX2
    for fichero in (maestra, mapa, reparto):
        if not fichero.is_file():
            raise ErrorDeProyecto(
                f"la etapa `{glb_final.ETAPA}` declara {fichero.name} y no esta en su "
                "directorio: un informe sin su fichero no es un artefacto"
            )

    # El paquete se escribe aparte y se renombra al acabar. Dentro, el manifiesto va el
    # ultimo: hasta que no esta, lo que hay es un directorio con ficheros, no un asset.
    paquete.parent.mkdir(parents=True, exist_ok=True)
    provisional = pathlib.Path(tempfile.mkdtemp(prefix=f".{nombre}.", dir=paquete.parent))
    _copiar_la_maestra(provisional, maestra, mapa)
    if perfiles.PIEZA_REPARTO in piezas:
        shutil.copy2(reparto, provisional / glb_final.GLB_KTX2)

    artefactos = [
        activo.describir_artefacto(
            provisional,
            glb_final.GLB_SIN_KTX2,
            identidad=perfiles.PIEZA_MAESTRA,
            rol="MASTER",
            formato="GLB",
        ),
        activo.describir_artefacto(
            provisional, normales.MAPA, identidad=normales.MAPA, rol="TEXTURE", usage="NORMAL"
        ),
    ]
    asset = activo.escribir_activo(
        provisional,
        identidad=nombre,
        productor=PRODUCTOR,
        version_del_productor=VERSION,
        artefactos=artefactos,
        destino=destino,
        materiales=[
            {
                "id": "material-de-la-superficie",
                "appliesTo": [perfiles.PIEZA_MAESTRA],
                "textures": {"normal": normales.MAPA},
                "wrap": "REPEAT",
                "alphaMode": "OPAQUE",
            }
        ],
        derivacion={
            "tool": f"videomesh/publicacion · gltfpack {glb_final.VERSION} nativo",
            "note": (
                "el asset que la cadena produjo, sellado contra el destino declarado; los "
                "bytes y los hashes salen del disco y el manifiesto se escribio el ultimo"
            ),
        },
    )

    # El validador externo, sobre la maestra **y** sobre la variante de reparto. La
    # segunda no entra en el manifiesto —su lector no puede abrirla—, pero su informe se
    # publica: su estado es parte de lo que este paquete declara de si mismo.
    validacion = _validar(directorio, provisional / glb_final.GLB_SIN_KTX2, VALIDACION)
    validacion_reparto = _validar(
        directorio, provisional / glb_final.GLB_KTX2, VALIDACION_DE_REPARTO
    )
    _swap(provisional, paquete)

    juicio, motivo = _juzgar(
        paquete / activo.ACTIVO,
        herramienta_de_produccion,
        directorio / VALIDACION if validacion is not None else None,
    )
    veredicto = _veredicto(juicio, motivo, directorio, validacion=validacion)
    duracion = time.monotonic() - empezado

    bytes_del_asset = (paquete / activo.ACTIVO).read_bytes()
    salida_del_paquete = {
        "id": "paquete",
        "ruta": f"{PAQUETES}/{nombre}",
        "bytes": len(bytes_del_asset),
        "sha256": hashlib.sha256(bytes_del_asset).hexdigest(),
    }

    registrar_stage(
        ruta,
        EjecucionDeStage(
            stage=ETAPA,
            estado=EstadoDeStage.COMPLETE,
            hash_de_entrada=huella,
            hash_de_salida=str(salida_del_paquete["sha256"]),
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
            artefacto=f"{PAQUETES}/{nombre}/{activo.ACTIVO}",
            estado=EstadoDeProcedencia.DERIVADO,
            productor=PRODUCTOR,
            version_del_productor=VERSION,
            package_id=None,
            fuente=str(paquete),
            ruta_del_artefacto=f"{PAQUETES}/{nombre}/{activo.ACTIVO}",
            sha256_del_artefacto=str(salida_del_paquete["sha256"]),
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
                {"etapa": glb_final.ETAPA, "sha256": str(entradas["maestra"]["sha256"])},
                {"etapa": glb_final.ETAPA, "sha256": str(entradas["mapa"]["sha256"])},
            ],
            "salidas": [salida_del_paquete],
            "medidas": {
                "destino": nombre,
                "perfil": _perfil_declarado(nombre),
                "paquete": f"{PAQUETES}/{nombre}",
                "piezas": list(piezas),
                "manifiesto": asset.name,
                "veredicto": veredicto,
                "validacion_externa": validacion,
                "validacion_externa_de_reparto": validacion_reparto,
                "duracion_s": duracion,
            },
            "purely_reconstructed": True,
            "procedencia": {
                "estado": EstadoDeProcedencia.DERIVADO.value,
                "productor": PRODUCTOR,
                "version_del_productor": VERSION,
            },
            "veredicto_del_vecino": _resumen_para_el_informe(juicio, motivo),
            "notas": [
                "el manifiesto se escribe el ultimo y sus bytes y sha256 se leen del disco: "
                "lo que declara es lo que hay",
                "el validador de Khronos se ejecuta y su informe viaja al vecino por "
                "`--external`: sin el, su readiness no aprueba (R15)",
                "la variante de reparto viaja en el paquete y **no** se declara como artifact: "
                "su lector no puede abrirla, y un artifact ilegible le revienta el informe "
                "entero en vez de darle un NOT_RUN",
            ],
            "no_comprobado": _no_comprobado(veredicto, validacion, validacion_reparto),
        },
    )


def _perfil_declarado(nombre: str) -> str | None:
    """De qué perfil salen los números del destino, si es un destino declarado."""
    destino = perfiles.DESTINOS.get(nombre)
    return None if destino is None else destino.perfil


def _validar(directorio: pathlib.Path, fichero: pathlib.Path, nombre: str) -> dict[str, Any] | None:
    """Valida un GLB y guarda su informe. `None` cuando el validador no está.

    Se escribe el informe del validador tal cual: es lo que se le pasa al vecino por
    `--external` y lo que queda como prueba de lo que se dijo del fichero.
    """
    try:
        informe = gltf_validator.validar(fichero)
    except MedicionNoDisponible:
        return None
    (directorio / nombre).write_text(json.dumps(informe, indent=2) + "\n", encoding="utf-8")
    return gltf_validator.resumen(informe, fichero=fichero.name)


def _juzgar(
    asset: pathlib.Path,
    herramienta: pathlib.Path | None,
    validacion_externa: pathlib.Path | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Le pasa el asset al vecino, con el informe del validador si lo hay."""
    try:
        return (
            softsight.juicio_de_produccion(
                asset, herramienta=herramienta, validacion_externa=validacion_externa
            ),
            None,
        )
    except MedicionNoDisponible as fallo:
        return None, str(fallo)


def _resumen_para_el_informe(juicio: dict[str, Any] | None, motivo: str | None) -> dict[str, Any]:
    """La misma forma que publican las etapas anteriores, para que la CLI la lea igual.

    El juicio crudo lleva el informe de produccion **anidado**, y ese documento ya vive
    en `produccion.json` — escribirlo aqui otra vez seria la unica etapa que guarda dos
    veces lo mismo, y la copia que envejece primero es la que miente. Se guarda el
    juicio sin su informe: estado, certificacion, comando y salidas, que es lo que la
    CLI lee y la prueba de con que veredicto se publico.
    """
    if juicio is None:
        return {"estado": "NOT_RUN", "motivo": motivo or "sin motivo declarado"}
    return {clave: valor for clave, valor in juicio.items() if clave != "informe"}


def _veredicto(
    juicio: dict[str, Any] | None,
    motivo: str | None,
    directorio: pathlib.Path,
    *,
    validacion: dict[str, Any] | None,
) -> dict[str, Any]:
    """El veredicto de la QA: `PRODUCTION_READY`, o lo que falte con su motivo.

    El estado se copia del `readiness` del vecino y **no se interpreta**: él decide qué
    es estar listo —la conjunción de sus comprobaciones—, y traducir aquí su veredicto
    sería un segundo criterio del mismo juicio.
    """
    if juicio is None:
        return {
            "estado": "NOT_RUN",
            "motivo": motivo or "sin motivo declarado",
            "falta": [
                {
                    "id": "veredicto_de_produccion",
                    "estado": "NOT_RUN",
                    "motivo": str(motivo or ""),
                }
            ],
            "validado_por": None if validacion is None else validacion["proveedor"],
        }
    informe: dict[str, Any] = juicio["informe"]
    (directorio / PRODUCCION).write_text(json.dumps(informe, indent=2) + "\n", encoding="utf-8")
    readiness = informe.get("readiness") or {}
    return {
        "estado": str(readiness.get("verdict", "UNKNOWN")),
        "certificacion": juicio["certificacion"],
        "motivo": readiness.get("reason"),
        "comando": juicio["comando"],
        "informe": PRODUCCION,
        "falta": _lo_que_falta(informe),
        "comprobaciones": {
            str(clave): valor for clave, valor in (readiness.get("byState") or {}).items()
        },
        "validado_por": None if validacion is None else validacion["proveedor"],
        # Lo que **el vecino dice** haber ingerido, y no lo que se le pasó: un
        # `--external` que su versión no leyera saldría aquí como ausente en vez de como
        # aprobado, y esa diferencia es la que separa una aprobación de una suposición.
        "validacion_leida_por_el_vecino": softsight.validacion_que_pediste(informe),
        "materialIssues": informe.get("materialIssues", []),
    }


def _no_comprobado(
    veredicto: dict[str, Any],
    validacion: dict[str, Any] | None,
    validacion_reparto: dict[str, Any] | None,
) -> list[dict[str, str]]:
    """Lo que esta etapa **no** pudo comprobar, con su motivo. Una lista vacía es una afirmación."""
    pendientes: list[dict[str, str]] = []
    if veredicto["estado"] == "NOT_RUN":
        pendientes.append(
            {"que": "veredicto_de_produccion", "motivo": str(veredicto.get("motivo", ""))}
        )
    if validacion is None:
        pendientes.append(
            {
                "que": "validacion_externa",
                "motivo": gltf_validator.motivo_de_ausencia() or "sin validador externo",
            }
        )
    contado = (
        f"cuenta {validacion_reparto['errores']} errores sobre ella"
        if validacion_reparto is not None
        else "no pudo contar nada sobre ella"
    )
    pendientes.append(
        {
            "que": glb_final.GLB_KTX2,
            "motivo": (
                "`NOT_RUN` por su consumidor, y se declara: el cargador de SoftSight rechaza "
                "`KHR_texture_basisu` por su nombre, asi que **no** puede juzgar esa variante. "
                f"El paquete la lleva y el validador de Khronos {contado}, pero eso no es la "
                "auditoria del vecino: quien la reparta, lo hace sin ella"
            ),
        }
    )
    return pendientes
