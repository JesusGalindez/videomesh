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
import shutil
from dataclasses import dataclass
from typing import Any

from videomesh.contracts.estado import (
    combinacion_declarada,
    combinaciones_admitidas,
    version_del_paquete,
)
from videomesh.contracts.generacion import ESQUEMAS

__all__ = ["Comprobacion", "informe_de_doctor"]


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


def _softsight() -> list[Comprobacion]:
    filas = []
    consumidor = ESQUEMAS.parent / "tools" / "reconstruction.mjs"
    if consumidor.is_file():
        filas.append(Comprobacion("SoftSight, consumidor", "DISPONIBLE", str(consumidor), True))
    else:
        filas.append(
            Comprobacion(
                "SoftSight, consumidor",
                "AUSENTE",
                "sin el no hay puerta: un paquete que nadie consume no esta comprobado",
                True,
            )
        )

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
        if c.bloquea and c.estado in ("AUSENTE", "NO COINCIDE", "INCOMPATIBLE")
    ]
    return {
        "documentType": "videomesh.doctor",
        "listo": not bloqueado,
        "comprobaciones": [
            {"que": c.que, "estado": c.estado, "detalle": c.detalle, "bloquea": c.bloquea}
            for c in comprobaciones
        ],
    }
