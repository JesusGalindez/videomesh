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

from videomesh.contracts.estado import (
    combinacion_declarada,
    combinaciones_admitidas,
    version_del_paquete,
)
from videomesh.contracts.generacion import ESQUEMAS

__all__ = ["Comprobacion", "importes_sin_resolver", "informe_de_doctor"]

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


def _softsight() -> list[Comprobacion]:
    filas = [_consumidor()]

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
