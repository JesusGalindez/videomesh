"""El GLB final — encargo 04, E3. Empaqueta con `gltfpack` y **no lo juzga**.

El instrumento está comprobado, y con la trampa que el encargo ya preveía: el
`gltfpack` de **npm no trae BasisU** — su propio wasm lo dice, «node.js builds do not
support BasisU due to lack of platform features» — y el binario **nativo** de
meshoptimizer sí. Esta etapa exige el nativo, y su frontera dice cómo se consigue.

Produce las dos variantes de la misma pasada:

```text
malla-sin-ktx2.glb   la auditable: sin KHR_texture_basisu, el cargador del vecino
                     la lee entera
malla-ktx2.glb       la de reparto: KTX2 en UASTC + meshopt, la que el cargador del
                     vecino RECHAZA por nombre — y por eso su veredicto sobre ella
                     sería NOT_RUN con ese motivo, nunca un verde mudo
```

**Por qué las dos no llevan las mismas banderas**, que es la decisión de esta etapa, y
está **medida** y no supuesta. El cargador del vecino —lo dice su `glbLoader.ts`— no trae
decodificador de `EXT_meshopt_compression`, así que comprimir la malla deja el GLB en
`extensionsRequired` y su auditoría no lo abre. Y el respaldo (`-cf`) tampoco lo
arregla: gltfpack lo escribe en un `.bin` **aparte**, y su lector solo admite GLB
autocontenido — medido las dos veces, la segunda sobre la salida real de esta etapa.
Así que la variante auditable es la que no comprime la malla; la de reparto va con
`-cc`, porque su consumidor es un motor con el decodificador, y su textura en **UASTC**
(`-tu`) y no en ETC1S: un mapa de normales son datos y no color, y ETC1S los destroza
en bloques de paleta.

Lo que **no** cambia entre las dos es lo que se audita: las dos cuantizan con los mismos
topes por defecto (`-vp 14 -vt 12 -vn 8`), así que los valores que el vecino lee de la
variante auditable son los que viajan en la de reparto — meshopt codifica esos mismos
enteros, no otros. Ni un vértice de diferencia, y el recuento de triángulos se publica
**contado del fichero**, uno por variante, en vez de prometido.

**La textura viaja incrustada.** El mapa de `normales` vive como artifact aparte y el
vecino lo decodifica suelto; para el reparto hace falta dentro del GLB. El `.gltf` que
se le pasa a gltfpack se escribe aquí con la imagen referida — es un **transporte** de
la etapa, vive en su directorio mientras corre y se borra al acabar. No es un segundo
escritor de GLB: los arreglos son los del GLB de `normales`, leído con el lector que
este repositorio ya tiene, y la normal que transporta es **la misma con la que se
construyó el marco** — recalcularla aquí sería otro dato.

Las convenciones de ejes ya viven en `adapters/gltf_transforms.py` (D32) y aquí no se
escribe una segunda: lo que se transporta son los arreglos de una pieza que ya está en
coordenadas de glTF.
"""

import hashlib
import json
import pathlib
import shutil
import subprocess
import time
from typing import Any

from videomesh.adapters import glb, softsight
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

__all__ = [
    "ETAPA",
    "GLB_KTX2",
    "GLB_SIN_KTX2",
    "Gltfpack",
    "digest_de_la_entrada",
    "empaquetar",
    "motivo_de_ausencia",
]


ETAPA = "glb"

PRODUCTOR = "videomesh/glb"

#: La pieza auditable y la de reparto. Los nombres dicen la diferencia: el códec de
#: texturas, que es lo único que cambia entre las dos.
GLB_SIN_KTX2 = "malla-sin-ktx2.glb"
GLB_KTX2 = "malla-ktx2.glb"

#: La identidad de la maestra dentro del asset del vecino. La misma que en la etapa de
#: material: el material declara `appliesTo: ["maestra"]`, y una identidad distinta
#: aquí dejaría su `auditMaterials` sin nada que atar.
IDENTIDAD_DE_LA_MAESTRA = "maestra"

#: La identidad con la que `normales` declara su malla en el informe. Es la de
#: `describir_malla` —que es quien la escribe— y no la del artifact del asset, que es
#: `maestra`: el informe describe ficheros y el asset declara papeles.
IDENTIDAD_DE_LA_PIEZA = "malla"

#: El informe del vecino, junto al asset que juzgó.
PRODUCCION = "produccion.json"

#: La versión del instrumento, medida: `gltfpack` sin argumentos la imprime y es `1.2`.
VERSION = "1.2"

#: El transporte: ficheros de la pasada, no artefactos. Se borran al acabar.
_TRANSPORTE = "transporte.gltf"
_TRANSPORTE_BIN = "transporte.bin"

#: Las banderas de la pasada auditable: **ninguna**. Y no es un descuido, es lo que se
#: midió: comprimir la malla con meshopt deja el GLB en `extensionsRequired`, y el
#: cargador del vecino no trae decodificador —`-cf` le añade un respaldo, pero gltfpack
#: lo escribe en un `.bin` **aparte**, y su lector solo admite GLB autocontenido—. Así
#: que la única pasada que su auditoría puede leer entera es la que no comprime la
#: malla. Lo que sí lleva es la cuantización por defecto (`-vp 14 -vt 12 -vn 8`), la
#: misma que la de reparto: **los valores que se auditan son los mismos**.
BANDERAS_AUDITABLE: tuple[str, ...] = ()

#: Las de la de reparto: meshopt sin respaldo y la textura en KTX2 con UASTC (`-tu`)
#: porque una normal en ETC1S sale con relieve falso sobre las superficies lisas.
BANDERAS_REPARTO: tuple[str, ...] = ("-cc", "-tc", "-tu")


class Gltfpack:
    """La frontera del instrumento externo, con las tres partes del mensaje.

    El binario va en una variable de clase a propósito: así el caso rojo se escribe sin
    desinstalar nada — la prueba apunta la frontera a una ruta que no existe y ve el
    mensaje.
    """

    proveedor = "meshoptimizer/gltfpack"

    binario = pathlib.Path(__file__).resolve().parents[3] / "tools-bin" / "native" / "gltfpack"

    #: Cómo se consigue, cuando falta. Se escribe una vez y la citan `exigir` y el
    #: `doctor` — una etapa sin instrumento se declara, y decir cómo se pone es parte
    #: de la declaración.
    instalacion = (
        "binario nativo de meshoptimizer/releases (el paquete de npm NO sirve: sin "
        "BasisU, lo dice su propio wasm), en tools-bin/native/gltfpack"
    )

    @classmethod
    def exigir(cls) -> pathlib.Path:
        """El binario, o un `MedicionNoDisponible` que dice qué falta y cómo se pone."""
        if not cls.binario.is_file():
            raise MedicionNoDisponible(
                f"falta el binario `gltfpack` nativo en {cls.binario}, que es el instrumento "
                "con el que esta etapa empaqueta el GLB final (meshoptimizer + KTX2).\n"
                f"  se instala con: {cls.instalacion}\n"
                "  `videomesh doctor` dice el resto del entorno de una vez"
            )
        return cls.binario

    @classmethod
    def instalado(cls) -> bool:
        """Si el instrumento está. Es una consulta al disco y no ejecuta nada."""
        return cls.binario.is_file()


def motivo_de_ausencia() -> str | None:
    """Por qué esta etapa no se puede hacer hoy, o `None` si sí.

    Es la consulta que la cadena usa para declararla `SIN_INSTRUMENTO` sin lanzarla, y
    por eso no ejecuta nada: mira si el binario está.
    """
    if Gltfpack.instalado():
        return None
    return (
        "falta el binario `gltfpack` nativo de meshoptimizer, y sin él no hay "
        "meshoptimizer ni KTX2 que ofrecer: " + Gltfpack.instalacion
    )


def _arreglo_al_transporte(
    documento: dict[str, Any], crudo: bytearray, datos: Any, *, tipo: str, forma: str
) -> int:
    """Añade un arreglo al transporte y devuelve el índice de su vista de búfer.

    El relleno a cuatro bytes es del formato y se hace aquí, en el único sitio que
    escribe el búfer: una vista desalineada la rechaza el propio gltfpack, y el fallo
    aparecería en su salida y no en la etapa.
    """
    while len(crudo) % 4 != 0:
        crudo.append(0)
    cuerpo = datos.astype("<f4" if tipo != "indices" else "<u4").tobytes()
    documento["bufferViews"].append(
        {
            "buffer": 0,
            "byteOffset": len(crudo),
            "byteLength": len(cuerpo),
            "target": 34963 if tipo == "indices" else 34962,
        }
    )
    return len(documento["bufferViews"]) - 1


def _transporte(directorio: pathlib.Path, pieza: glb.Pieza, mapa: pathlib.Path) -> pathlib.Path:
    """El `.gltf` que gltfpack lee: la pieza de `normales` y su mapa, referidos.

    Sin la textura declarada, `-tc` no tiene nada que comprimir y la variante de
    reparto saldría con el nombre `ktx2` y sin una sola imagen KTX2 dentro: un fichero
    que miente en su nombre. Por eso el mapa se declara como `normalTexture` — que es
    lo que es — y no como un adjunto cualquiera.
    """
    import numpy as np

    if pieza.normales is None:
        raise ErrorDeProyecto(
            "la pieza de `normales` no trae normales y el GLB final las necesita: el mapa "
            "horneado se lee contra la normal de la malla, y sin ella el visor se la "
            "inventa y el relieve sale desplazado sin que nada lo diga"
        )

    documento: dict[str, Any] = {
        "asset": {"version": "2.0", "generator": "videomesh/glb"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{"name": "pieza", "primitives": [{"attributes": {}, "material": 0}]}],
        "materials": [{"name": "material-de-la-superficie", "normalTexture": {"index": 0}}],
        "textures": [{"source": 0}],
        "images": [{"uri": mapa.name}],
        "accessors": [],
        "bufferViews": [],
        "buffers": [],
    }
    primitiva = documento["meshes"][0]["primitives"][0]

    crudo = bytearray()

    # Los atributos en el orden del formato, y los índices al final: el orden importa
    # porque los índices de los accesors viajan en el JSON.
    for atributo, datos, forma in (
        ("POSITION", pieza.vertices, "VEC3"),
        ("TEXCOORD_0", pieza.uv, "VEC2"),
        ("NORMAL", pieza.normales, "VEC3"),
    ):
        arreglo = np.asarray(datos, dtype="<f4").reshape(-1, {"VEC3": 3, "VEC2": 2}[forma])
        vista = _arreglo_al_transporte(documento, crudo, arreglo, tipo="atributo", forma=forma)
        accesor = {
            "bufferView": vista,
            "componentType": 5126,
            "count": int(arreglo.shape[0]),
            "type": forma,
        }
        if atributo == "POSITION":
            accesor["min"] = [float(x) for x in arreglo.min(axis=0)]
            accesor["max"] = [float(x) for x in arreglo.max(axis=0)]
        documento["accessors"].append(accesor)
        primitiva["attributes"][atributo] = len(documento["accessors"]) - 1
        crudo.extend(arreglo.tobytes())

    indices = np.asarray(pieza.triangulos, dtype="<u4").reshape(-1, 3)
    vista = _arreglo_al_transporte(documento, crudo, indices, tipo="indices", forma="SCALAR")
    documento["accessors"].append(
        {
            "bufferView": vista,
            "componentType": 5125,
            "count": int(indices.size),
            "type": "SCALAR",
        }
    )
    primitiva["indices"] = len(documento["accessors"]) - 1
    crudo.extend(indices.tobytes())

    documento["buffers"] = [{"byteLength": len(crudo), "uri": _TRANSPORTE_BIN}]
    directorio.mkdir(parents=True, exist_ok=True)
    (directorio / _TRANSPORTE_BIN).write_bytes(bytes(crudo))
    ruta = directorio / _TRANSPORTE
    ruta.write_text(json.dumps(documento), encoding="utf-8")
    return ruta


def _lado_de_textura(destino: dict[str, Any]) -> list[str]:
    """Las banderas de textura que el destino manda, y ninguna más.

    El encargo avisa del orden: si se redimensionan las texturas, va **antes** de
    comprimir — un reescritor que toque el GLB comprimido busca los desplazamientos
    donde no están y produce un fichero que revienta al cargar. Aquí el redimensionado
    lo hace el propio gltfpack con `-tl`, así que el orden no se puede equivocar.
    """
    banderas: list[str] = []
    lado = destino.get("textureMaxSize")
    if isinstance(lado, int) and lado > 0:
        banderas += ["-tl", str(lado)]
    if destino.get("texturePowerOfTwo"):
        banderas.append("-tp")
    return banderas


def _correr(
    binario: pathlib.Path, entrada: pathlib.Path, salida: pathlib.Path, banderas: list[str]
) -> None:
    """Una pasada de gltfpack. Su salida se lee cuando falla, y no se traga nunca."""
    orden = [str(binario), "-i", str(entrada), "-o", str(salida), *banderas]
    ejecucion = subprocess.run(orden, capture_output=True, text=True, check=False)
    if ejecucion.returncode != 0:
        raise ErrorDeProyecto(
            f"gltfpack salió {ejecucion.returncode} con {' '.join(orden)}: "
            f"{ejecucion.stderr.strip()[-400:] or ejecucion.stdout.strip()[-400:]}"
        )


def _variantes(
    binario: pathlib.Path,
    transporte: pathlib.Path,
    directorio: pathlib.Path,
    destino: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Las dos pasadas: la auditable y la de reparto. Misma geometría, otro códec."""
    # La auditable, comprimida CON respaldo: el cargador del vecino no trae decodificador
    # de EXT_meshopt_compression, y `-cf` es lo que deja el mismo flujo en claro.
    _correr(binario, transporte, directorio / GLB_SIN_KTX2, list(BANDERAS_AUDITABLE))
    # La de reparto, sin respaldo y con UASTC: su consumidor es un motor con decodificador,
    # y una normal en ETC1S sale con relieve falso sobre las superficies lisas. El tope de
    # textura del destino se aplica **aquí y no en la auditable**, y no por descuido:
    # gltfpack solo redimensiona una textura cuando la va a recodificar —«Texture
    # processing is only supported when texture compression is enabled»—, así que el
    # redimensionado vive donde vive el códec, y el orden que el encargo avisa (redimensionar
    # antes de comprimir) lo cumple la propia herramienta en la misma pasada.
    _correr(
        binario, transporte, directorio / GLB_KTX2, [*BANDERAS_REPARTO, *_lado_de_textura(destino)]
    )
    return (
        _medidas_del_glb(directorio / GLB_SIN_KTX2, ktx2=False),
        _medidas_del_glb(directorio / GLB_KTX2, ktx2=True),
    )


def _documento_del_glb(ruta: pathlib.Path) -> tuple[bytes, dict[str, Any]]:
    """El JSON de un GLB, y sus bytes. Los dos bloques se leen donde el formato los pone."""
    datos = ruta.read_bytes()
    largo_json = int.from_bytes(datos[12:16], "little")
    return datos, json.loads(datos[20 : 20 + largo_json])


def _medidas_del_glb(ruta: pathlib.Path, *, ktx2: bool) -> dict[str, Any]:
    """Lo que el fichero producido dice de sí mismo: bytes, triángulos, extensiones.

    Los triángulos se **cuentan del fichero** —el accesor de índices de la primera
    primitiva— y no se copian de lo que se le pidió a gltfpack: una cifra prometida no
    es una cifra medida, y esta etapa existe para publicar lo que hay.
    """
    datos, documento = _documento_del_glb(ruta)
    primitiva = documento["meshes"][0]["primitives"][0]
    triangulos = (
        documento["accessors"][primitiva["indices"]]["count"] // 3 if "indices" in primitiva else 0
    )
    return {
        "ruta": ruta.name,
        "bytes": len(datos),
        "triangulos": int(triangulos),
        "vertices": int(documento["accessors"][primitiva["attributes"]["POSITION"]]["count"]),
        "extensiones": list(documento.get("extensionsUsed", [])),
        "extensiones_requeridas": list(documento.get("extensionsRequired", [])),
        "ktx2": ktx2,
    }


def _la_etapa_anterior(proyecto: pathlib.Path) -> dict[str, dict[str, Any]]:
    """La pieza y el mapa que `normales` publicó, **leídos declarados en su informe**.

    No se rehashea el fichero: el hash ya lo calculó quien lo escribió, y volver a
    calcularlo daría dos cifras de lo mismo. Lo que sí se hace es leer el GLB, porque su
    contenido viaja al transporte y un fichero que no se puede leer se descubre aquí y no
    en la salida de gltfpack.
    """
    pieza = salida_de(proyecto, normales.ETAPA, identidad=IDENTIDAD_DE_LA_PIEZA)
    mapa = salida_de(proyecto, normales.ETAPA, identidad=normales.MAPA)
    if pieza is None or mapa is None:
        raise ErrorDeProyecto(
            "no hay etapa `normales` de la que partir: el GLB final empaqueta la pieza con "
            "atlas y su mapa, y sin ellos no hay nada que empaquetar"
        )
    return {"pieza": pieza, "mapa": mapa}


def digest_de_la_entrada(proyecto: pathlib.Path, *, parametros: dict[str, Any]) -> str | None:
    """El hash de entrada de la etapa con esos parámetros, o `None` si falta la anterior."""
    try:
        entradas = _la_etapa_anterior(proyecto)
    except ErrorDeProyecto:
        return None
    return hash_de_entrada(
        entradas=[str(entradas["pieza"]["sha256"]), str(entradas["mapa"]["sha256"])],
        parametros=parametros,
        proveedor=PRODUCTOR,
        version_del_proveedor=VERSION,
    )


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
    *,
    variante: str,
) -> dict[str, Any]:
    """El veredicto del vecino sobre la variante legible, o su `NOT_RUN` con el motivo."""
    if juicio is None:
        return {
            "estado": "NOT_RUN",
            "motivo": motivo or "sin motivo declarado",
            "variante": variante,
        }
    informe: dict[str, Any] = juicio["informe"]
    (directorio / PRODUCCION).write_text(json.dumps(informe, indent=2) + "\n", encoding="utf-8")
    return {
        "estado": "MEDIDO",
        "certificacion": juicio["certificacion"],
        "motivo": juicio["motivo"],
        "comando": juicio["comando"],
        "informe": PRODUCCION,
        # Sobre qué fichero se juzgó. La variante con KTX2 la rechaza su cargador por
        # nombre, así que su veredicto es `NOT_RUN` y se publica como tal — nunca como
        # un verde por no haber mirado.
        "variante": variante,
        "readiness": (informe.get("readiness") or {}).get("verdict"),
        "materialIssues": informe.get("materialIssues", []),
    }


def _no_comprobado(veredicto: dict[str, Any], con_ktx2: dict[str, Any]) -> list[dict[str, str]]:
    """Lo que esta etapa no miró, con su motivo. Una lista vacía es una afirmación."""
    pendientes: list[dict[str, str]] = []
    if veredicto["estado"] != "MEDIDO":
        pendientes.append(
            {"que": "veredicto_de_produccion", "motivo": str(veredicto.get("motivo", ""))}
        )
    pendientes.append(
        {
            "que": GLB_KTX2,
            "motivo": (
                "`NOT_RUN` por su consumidor, y se declara: el cargador de SoftSight rechaza "
                "KHR_texture_basisu por su nombre, así que **no** puede juzgar esa variante. La "
                "geometría que hay dentro es la de la variante auditada —misma cuantización y "
                f"mismos {con_ktx2['triangulos']} triángulos—, pero eso es una afirmación de esta "
                "etapa y no un veredicto del vecino: quien reparta el KTX2 lo hace sin su auditoría"
            ),
        }
    )
    return pendientes


def empaquetar(
    proyecto: pathlib.Path,
    *,
    destino: dict[str, Any],
    herramienta: pathlib.Path | None = None,
    herramienta_de_produccion: pathlib.Path | None = None,
) -> pathlib.Path:
    """Empaqueta el GLB final en sus dos variantes, y devuelve su informe.

    El destino manda —los topes de textura salen de él y entran en el hash de entrada—,
    porque un mismo asset empaquetado para web y para juego no es el mismo fichero, y
    cambiar el destino tiene que caducar la etapa.
    """
    ruta = pathlib.Path(proyecto)
    proyecto_abierto = abrir_proyecto(ruta)
    binario = herramienta if herramienta is not None else Gltfpack.exigir()

    entradas = _la_etapa_anterior(ruta)
    parametros: dict[str, Any] = {
        "destino": json.loads(json.dumps(destino)),
        "gltfpack": VERSION,
    }
    huella = hash_de_entrada(
        entradas=[str(entradas["pieza"]["sha256"]), str(entradas["mapa"]["sha256"])],
        parametros=parametros,
        proveedor=PRODUCTOR,
        version_del_proveedor=VERSION,
    )

    anterior = ultima_de(ruta, ETAPA)
    # El registro dice si la entrada cambió; no dice si lo que produjo sigue en su sitio.
    falta_lo_producido = leer_informe(ruta, ETAPA) is None or any(
        not (directorio_de_etapa(ruta, ETAPA) / nombre).is_file()
        for nombre in (GLB_SIN_KTX2, GLB_KTX2)
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
    directorio.mkdir(parents=True, exist_ok=True)

    # La pieza y el mapa, al directorio de la etapa: gltfpack los lee desde aquí, y el
    # mapa se copia antes porque su nombre viaja en la uri del transporte.
    maestra = malla_de_la_etapa(ruta, normales.ETAPA).parent / normales.GLB
    mapa_origen = malla_de_la_etapa(ruta, normales.ETAPA).parent / normales.MAPA
    shutil.copy2(mapa_origen, directorio / normales.MAPA)
    pieza = glb.leer_glb(maestra)
    transporte = _transporte(directorio, pieza, directorio / normales.MAPA)

    sin, con = _variantes(binario, transporte, directorio, destino)

    # El transporte es de la pasada, no un artefacto: no se publica y no se queda.
    (directorio / _TRANSPORTE).unlink(missing_ok=True)
    (directorio / _TRANSPORTE_BIN).unlink(missing_ok=True)

    salida_sin = activo.describir_artefacto(
        directorio, GLB_SIN_KTX2, identidad=IDENTIDAD_DE_LA_MAESTRA, rol="MASTER", formato="GLB"
    )
    salida_con = activo.describir_artefacto(
        directorio, GLB_KTX2, identidad=GLB_KTX2, rol="MASTER", formato="GLB"
    )
    salida_del_mapa = activo.describir_artefacto(
        directorio, normales.MAPA, identidad=normales.MAPA, rol="TEXTURE", usage="NORMAL"
    )

    asset = activo.escribir_activo(
        directorio,
        identidad=f"{proyecto_abierto.nombre}·{ETAPA}",
        productor=PRODUCTOR,
        version_del_productor=VERSION,
        # Al vecino se le declara **lo que puede leer**: la variante auditable y su mapa.
        # La de reparto no entra en el manifiesto, y no por comodidad: su cargador la
        # rechaza por nombre, y un artifact que no se puede abrir no le da un NOT_RUN,
        # le revienta el informe entero. Su veredicto se publica aparte, en
        # `no_comprobado`, que es donde se dice lo que no se miró.
        artefactos=[salida_sin, salida_del_mapa],
        destino=destino,
        materiales=[
            {
                "id": "material-de-la-superficie",
                "appliesTo": [IDENTIDAD_DE_LA_MAESTRA],
                "textures": {"normal": normales.MAPA},
                "wrap": "REPEAT",
                "alphaMode": "OPAQUE",
            }
        ],
        derivacion={
            "tool": f"videomesh/glb · gltfpack {VERSION} nativo",
            "note": (
                "dos variantes de la misma pieza: la auditable sin compresion de malla y con "
                "la textura en PNG, la de reparto con meshopt y KTX2. Misma cuantizacion, "
                "mismos vertices"
            ),
        },
    )

    # El veredicto del vecino corre sobre la variante AUDITABLE: el cargador de SoftSight
    # rechaza KHR_texture_basisu por nombre, y un verde sobre lo que no se puede leer
    # sería el verde mudo que el encargo prohíbe.
    juicio, motivo = _juzgar(asset, herramienta_de_produccion)
    veredicto = _veredicto(juicio, motivo, directorio, variante=GLB_SIN_KTX2)
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
            artefacto=GLB_KTX2,
            # Empaquetar es derivar: los dos ficheros salen de la pieza y del mapa de la
            # etapa anterior, y lo que añade esta etapa es el códec y el contenedor.
            estado=EstadoDeProcedencia.DERIVADO,
            productor=PRODUCTOR,
            version_del_productor=VERSION,
            package_id=None,
            fuente=str(directorio),
            ruta_del_artefacto=GLB_KTX2,
            sha256_del_artefacto=str(salida_con["sha256"]),
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
                {"etapa": normales.ETAPA, "sha256": str(entradas["pieza"]["sha256"])},
                {"etapa": normales.ETAPA, "sha256": str(entradas["mapa"]["sha256"])},
            ],
            "salidas": [salida_del_asset, salida_sin, salida_con, salida_del_mapa],
            "medidas": {
                "sin_ktx2": sin,
                "con_ktx2": con,
                "banderas": {
                    GLB_SIN_KTX2: list(BANDERAS_AUDITABLE),
                    GLB_KTX2: [*BANDERAS_REPARTO, *_lado_de_textura(destino)],
                },
                "duracion_s": duracion,
            },
            "purely_reconstructed": True,
            "procedencia": {
                "estado": EstadoDeProcedencia.DERIVADO.value,
                "productor": PRODUCTOR,
                "version_del_productor": VERSION,
            },
            "veredicto_del_vecino": veredicto,
            "notas": [
                "el paquete de npm de gltfpack no sirve para KTX2: sin BasisU, lo dice su "
                "propio wasm. Esta etapa exige el binario nativo de meshoptimizer",
                "la variante auditable no comprime la malla: sin decodificador de meshopt en "
                "el cargador del vecino, y con el respaldo de -cf en un .bin aparte que su "
                "lector no admite, la unica pasada legible es la que no comprime",
                "la de reparto va sin respaldo y su textura en UASTC (-tu): un mapa de "
                "normales son datos y no color, y ETC1S los destroza en bloques de paleta",
                "la auditoria corre sobre la variante sin KTX2: el cargador del vecino "
                "rechaza KHR_texture_basisu por nombre, y sobre esa variante su veredicto "
                "seria NOT_RUN — nunca un verde por no haber mirado",
            ],
            "no_comprobado": _no_comprobado(veredicto, con),
        },
    )
