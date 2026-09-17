"""`videomesh doctor`: existencia **y** compatibilidad — §21 del roadmap.

Que un binario esté no dice nada. Un COLMAP instalado que escribe un formato que
no leemos es tan inútil como uno ausente, y la diferencia solo se ve
comprobándola. Por eso cada fila trae un estado y, cuando se puede, qué se
comparó.

La regla que le da sentido: **una incompatibilidad contractual conocida falla
pronto**, antes de las etapas caras. Descubrir que el hash del esquema no cuadra
después de dos horas de reconstrucción es descubrirlo tarde.

Lo que falta para etapas futuras se **reporta**, no se convierte en fallo de hoy:
COLMAP y FFmpeg no hacen falta para R0, que es JSON, hashes y álgebra.
"""

import hashlib
import json
import pathlib
import re
import shutil
from dataclasses import dataclass
from typing import Any

from videomesh.adapters import pymeshlab, xatlas
from videomesh.adapters.softsight import HERRAMIENTA
from videomesh.application import glb_final, retopologia, textura
from videomesh.contracts.estado import (
    combinacion_declarada,
    combinaciones_admitidas,
    version_del_paquete,
)
from videomesh.contracts.generacion import ESQUEMAS

__all__ = [
    "Comprobacion",
    "comprobar_herramienta_de_medida",
    "comprobar_paquete_de_referencia",
    "comprobar_proveedor",
    "importes_sin_resolver",
    "informe_de_doctor",
]

#: Un `from "..."` de un módulo ES. Solo interesan los **relativos**: `node:fs` y
#: los paquetes no son ficheros del repositorio, y buscarlos en disco daría un
#: ausente falso.
_IMPORTE = re.compile(r"""^\s*(?:import|export)\b[^;]*?from\s+["'](\.[^"']+)["']""", re.M | re.S)


@dataclass(frozen=True)
class Comprobacion:
    """Una fila del informe: qué se miró, cómo salió y si bloquea hoy."""

    que: str
    estado: str
    detalle: str = ""
    #: Si esto en rojo impide trabajar **hoy**. Lo de las etapas futuras, no.
    bloquea: bool = False


def _binario(nombre: str, orden: str, *, bloquea: bool) -> Comprobacion:
    ruta = shutil.which(orden)
    if ruta:
        return Comprobacion(nombre, "DISPONIBLE", ruta, bloquea)
    return Comprobacion(nombre, "AUSENTE", f"no se encuentra `{orden}` en el PATH", bloquea)


def importes_sin_resolver(texto: str, base: pathlib.Path) -> list[str]:
    """Los importes relativos del módulo que **no están en disco**, en orden.

    Recibe el texto y la base como argumentos a propósito: así el caso rojo se
    escribe sin mover nada de sitio, que es lo que distingue una comprobación de
    una que solo se ha visto verde.
    """
    return [
        especificador
        for especificador in _IMPORTE.findall(texto)
        if not (base / especificador).is_file()
    ]


def _proveedores() -> list[Comprobacion]:
    """Los tres proveedores de las etapas de malla y atlas, cada uno con su fila.

    Se importan los módulos y **no las librerías**: los adaptadores solo las importan
    dentro de las funciones que las usan, así que preguntar por ellas aquí no las trae
    — y `doctor` tiene que funcionar en un entorno sin el extra `malla` puesto.
    """
    return [
        comprobar_proveedor(
            "Proveedor de malla",
            nombre=pymeshlab.PROVEEDOR,
            instalado=pymeshlab.instalado(),
            version=pymeshlab.version(),
            instalacion=pymeshlab.INSTALACION,
            para="limpieza, decimado y las etapas de malla que vienen después",
        ),
        comprobar_proveedor(
            "Proveedor de UV",
            nombre=xatlas.PROVEEDOR,
            instalado=xatlas.instalado(),
            version=xatlas.version(),
            instalacion=xatlas.INSTALACION,
            para="cortar y empaquetar el atlas de coordenadas de textura",
        ),
        comprobar_proveedor(
            "Proveedor de retopología",
            nombre=retopologia.PROVEEDOR,
            instalado=retopologia.instalado(),
            # Ninguno de los dos sabe decir su versión de una forma que se pueda leer
            # sin ejecutarlo, y ejecutarlo para preguntarle sería otra cosa.
            version="",
            instalacion=retopologia.INSTALACION,
            para="convertir triángulos en quads alineados con la forma",
        ),
        comprobar_proveedor(
            "Proveedor de textura",
            nombre=textura.PROVEEDOR,
            instalado=textura.instalado(),
            version="",
            instalacion=textura.INSTALACION,
            para="proyectar los fotogramas reales sobre la malla",
        ),
        comprobar_proveedor(
            "Empaquetador de GLB",
            nombre=glb_final.Gltfpack.proveedor,
            instalado=glb_final.Gltfpack.instalado(),
            # Su versión sí se puede leer sin empaquetar nada: `gltfpack` sin argumentos
            # la imprime. Se declara la que esta cadena espera, que es la que midió.
            version=glb_final.VERSION,
            instalacion=glb_final.Gltfpack.instalacion,
            para="empaquetar el GLB final con meshoptimizer y KTX2",
        ),
    ]


def _consumidor() -> Comprobacion:
    """Que el consumidor **se pueda consumir**, no que el fichero esté.

    `tools/reconstruction.mjs` importa `../dist-node/agent3d.mjs`, que no viaja en
    el repositorio: lo escribe `npm run build:agent3d`. En un clon recién hecho el
    fichero está y el import no resuelve, así que mirar `is_file()` decía
    DISPONIBLE de algo que revienta al primer uso — y `doctor` es lo primero que
    corre un agente nuevo, así que su respuesta decide si se cree lo que viene
    después.
    """
    consumidor = ESQUEMAS.parent / "tools" / "reconstruction.mjs"
    if not consumidor.is_file():
        return Comprobacion(
            "SoftSight, consumidor",
            "AUSENTE",
            "sin el no hay puerta: un paquete que nadie consume no esta comprobado",
            True,
        )

    faltan = importes_sin_resolver(consumidor.read_text(encoding="utf-8"), consumidor.parent)
    if faltan:
        return Comprobacion(
            "SoftSight, consumidor",
            "SIN CONSTRUIR",
            f"el fichero esta pero no resuelve {', '.join(faltan)}; "
            "se construye con `npm run build:agent3d` en ../Dron/softsight",
            True,
        )
    return Comprobacion("SoftSight, consumidor", "DISPONIBLE", str(consumidor), True)


def comprobar_paquete_de_referencia(manifest: pathlib.Path) -> Comprobacion:
    """El paquete `cube-v1` de SoftSight, que es de dónde se lee qué forma tiene
    un paquete de verdad.

    Tampoco viaja: lo escribe `npm run cube-v1` y el `.gitignore` de SoftSight lo
    excluye porque el generador es determinista y commitearlo sería un segundo
    original. Seis ficheros de prueba lo abren **en tiempo de importación**, así
    que sin él la suite no arranca — y la primera ejecución del workflow lo
    demostró con `doctor` en verde delante.

    Recibe la ruta como argumento por lo de siempre: para que el caso rojo se
    pueda escribir sin mover el directorio de sitio.
    """
    if manifest.is_file():
        return Comprobacion("SoftSight, paquete de referencia", "DISPONIBLE", str(manifest), True)
    return Comprobacion(
        "SoftSight, paquete de referencia",
        "SIN CONSTRUIR",
        f"falta {manifest}; se escribe con `npm run cube-v1` en ../Dron/softsight. "
        "Sin el, seis ficheros de prueba no llegan ni a importarse",
        True,
    )


def comprobar_herramienta_de_medida(ruta: pathlib.Path) -> Comprobacion:
    """El fichero por el que `diffMeshes` de SoftSight mide la distancia.

    Es el instrumento del criterio de cierre del encargo 04 —«el número que dice
    cuánto se perdió»—, así que una etapa que decima o que mueve vértices depende
    de él. Sin él, `distancia_de_superficie` levanta `MedicionNoDisponible` y la
    etapa publica `NOT_RUN` con su motivo, que es correcto pero llega tarde: se
    descubre al correr la etapa en vez de al empezar el día.

    Recibe la ruta como argumento por lo de siempre: para que el caso rojo se
    escriba sin mover SoftSight de sitio.
    """
    if ruta.is_file():
        return Comprobacion("SoftSight, herramienta de medida", "DISPONIBLE", str(ruta), False)
    return Comprobacion(
        "SoftSight, herramienta de medida",
        "AUSENTE",
        f"falta {ruta}: es la puerta de medida del vecino, no una copia local. "
        "Sin ella las etapas de malla publican NOT_RUN en vez de su distancia",
        False,
    )


def comprobar_proveedor(
    que: str,
    *,
    nombre: str,
    instalado: bool,
    version: str,
    instalacion: str,
    para: str,
) -> Comprobacion:
    """Un proveedor de una etapa, sea un extra de Python o un programa de fuera.

    Los datos llegan por argumento —y no se leen del adaptador aquí dentro— porque así
    el caso rojo se escribe sin desinstalar nada. Se pregunta por el módulo y no se
    importa: `doctor` tiene que poder decir que falta sin que su propio informe dependa
    de que esté.

    La versión se publica porque **entra en el hash de entrada** de cada etapa (§9): un
    proveedor nuevo deja el registro describiendo una salida que ya no se produciría, y
    sin el número a la vista eso se lee como una etapa caducada sin motivo. Los que no
    saben decir su versión la dejan vacía, y la fila lo dice con el nombre solo.

    `bloquea=False` siempre, y por la misma razón que COLMAP y FFmpeg: lo que falta de
    una etapa de malla se **reporta**, y el paquete base —R0, que es JSON, hashes y
    álgebra— funciona sin ello.
    """
    if instalado:
        detalle = f"{nombre} {version}".strip()
        return Comprobacion(que, "DISPONIBLE", detalle, False)
    return Comprobacion(
        que,
        "AUSENTE",
        f"falta `{nombre}`, que hace falta para {para}.\n  se instala con: {instalacion}",
        False,
    )


def _softsight() -> list[Comprobacion]:
    filas = [
        _consumidor(),
        comprobar_paquete_de_referencia(
            ESQUEMAS.parent / "artifacts" / "cube-v1" / "manifest.json"
        ),
        comprobar_herramienta_de_medida(HERRAMIENTA),
    ]

    registro = ESQUEMAS / "registry.json"
    if not registro.is_file():
        return [*filas, Comprobacion("SoftSight, esquema", "AUSENTE", str(registro), True)]

    publicado = json.loads(registro.read_text(encoding="utf-8"))
    conocidos = {entrada["sha256"] for entrada in publicado["schemas"]}
    nuestro = hashlib.sha256(
        (ESQUEMAS / "reconstruction-package.schema.json").read_bytes()
    ).hexdigest()
    filas.append(
        Comprobacion(
            "SoftSight, hash del esquema",
            "COINCIDE" if nuestro in conocidos else "NO COINCIDE",
            nuestro[:12] + "...",
            True,
        )
    )

    declarada = combinacion_declarada()
    admitidas = combinaciones_admitidas()
    filas.append(
        Comprobacion(
            "SoftSight, combinacion de versiones",
            "COMPATIBLE" if declarada in admitidas else "INCOMPATIBLE",
            f"paquete {version_del_paquete()}",
            True,
        )
    )
    return filas


def informe_de_doctor() -> dict[str, Any]:
    """El informe entero, en la forma que lee una máquina."""
    comprobaciones = [
        *_softsight(),
        *_proveedores(),
        _binario("FFmpeg", "ffmpeg", bloquea=False),
        _binario("COLMAP", "colmap", bloquea=False),
        _binario("Node", "node", bloquea=True),
    ]
    bloqueado = [
        c
        for c in comprobaciones
        if c.bloquea and c.estado in ("AUSENTE", "SIN CONSTRUIR", "NO COINCIDE", "INCOMPATIBLE")
    ]
    return {
        "documentType": "videomesh.doctor",
        "listo": not bloqueado,
        "comprobaciones": [
            {"que": c.que, "estado": c.estado, "detalle": c.detalle, "bloquea": c.bloquea}
            for c in comprobaciones
        ],
    }
