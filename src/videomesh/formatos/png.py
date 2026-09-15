"""Escritura de PNG RGB de 8 bits, determinista y sin dependencias.

Se escribe a mano porque las imagenes de `cube-v1` son **evidencia** y tienen que
ser reproducibles byte a byte: un codificador con opciones por omision que cambien
entre versiones convertiria el sha256 del paquete en algo que depende de la
maquina.

Sin filtros por fila —byte 0 al principio de cada una— y con `zlib` a nivel fijo:
lo que se gana en tamano no compensa que dos generaciones puedan discrepar.
"""

import pathlib
import struct
import zlib
from collections.abc import Sequence

__all__ = ["escribir_png", "leer_dimensiones_png"]

_FIRMA = b"\x89PNG\r\n\x1a\n"
_NIVEL = 9

Color = tuple[int, int, int]


def _trozo(tipo: bytes, cuerpo: bytes) -> bytes:
    return (
        struct.pack(">I", len(cuerpo))
        + tipo
        + cuerpo
        + struct.pack(">I", zlib.crc32(tipo + cuerpo) & 0xFFFFFFFF)
    )


def escribir_png(destino: pathlib.Path, *, ancho: int, alto: int, pixeles: Sequence[Color]) -> None:
    """Escribe los pixeles fila a fila, de arriba a abajo."""
    if len(pixeles) != ancho * alto:
        raise ValueError(
            f"la rejilla es {ancho}x{alto} = {ancho * alto} pixeles y llegan {len(pixeles)}"
        )

    plano = bytearray()
    for fila in range(alto):
        plano.append(0)  # sin filtro
        for color in pixeles[fila * ancho : (fila + 1) * ancho]:
            plano.extend(bytes(color))

    cabecera = struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0)
    destino.write_bytes(
        _FIRMA
        + _trozo(b"IHDR", cabecera)
        + _trozo(b"IDAT", zlib.compress(bytes(plano), _NIVEL))
        + _trozo(b"IEND", b"")
    )


def leer_dimensiones_png(origen: pathlib.Path) -> tuple[int, int]:
    """La rejilla **real** del fichero, que es con la que D33 compara la camara."""
    crudo = origen.read_bytes()
    if crudo[:8] != _FIRMA:
        raise ValueError(f"{origen} no es un PNG")
    ancho, alto = struct.unpack(">II", crudo[16:24])
    return int(ancho), int(alto)
