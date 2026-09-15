"""Escritura de PLY en ASCII, determinista.

ASCII y no binario a proposito: el paquete es un fixture que alguien tiene que
poder abrir y leer para comprobar que dice lo que se afirma. 12,7 KB no justifican
un formato que solo entiende una libreria.

Los numeros se escriben con `repr` de Python y sin notacion cientifica. Un `1e-17`
es un numero valido y no todos los lectores de PLY lo interpretan igual, asi que
no se emite ninguno.
"""

import math
import pathlib
from collections.abc import Sequence

from videomesh.domain.malla import Malla, Punto

__all__ = ["escribir_ply_malla", "escribir_ply_nube", "leer_cabecera_ply"]

_DECIMALES = 6


def _numero(valor: float) -> str:
    if not math.isfinite(valor):
        raise ValueError(f"{valor} no es un numero finito y no se escribe en un PLY")
    texto = f"{valor:.{_DECIMALES}f}"
    # `-0.000000` es el mismo punto que `0.000000` y dos generaciones no pueden
    # discrepar en el signo de un cero.
    return "0.000000" if float(texto) == 0.0 else texto


def _cabecera(elementos: Sequence[tuple[str, int]]) -> list[str]:
    lineas = ["ply", "format ascii 1.0", "comment generado por videomesh"]
    for nombre, cantidad in elementos:
        lineas.append(f"element {nombre} {cantidad}")
        if nombre == "vertex":
            lineas += ["property float x", "property float y", "property float z"]
        else:
            lineas.append("property list uchar int vertex_indices")
    lineas.append("end_header")
    return lineas


def escribir_ply_malla(destino: pathlib.Path, malla: Malla) -> None:
    """Escribe la malla con sus vertices partidos por cara y sus triangulos."""
    lineas = _cabecera([("vertex", len(malla.vertices)), ("face", len(malla.triangulos))])
    lineas += [" ".join(_numero(c) for c in vertice) for vertice in malla.vertices]
    lineas += [f"3 {a} {b} {c}" for a, b, c in malla.triangulos]
    destino.write_text("\n".join(lineas) + "\n", encoding="ascii")


def escribir_ply_nube(destino: pathlib.Path, puntos: Sequence[Punto]) -> None:
    """Escribe una nube de puntos: sin caras, porque no tiene superficie."""
    lineas = _cabecera([("vertex", len(puntos))])
    lineas += [" ".join(_numero(c) for c in punto) for punto in puntos]
    destino.write_text("\n".join(lineas) + "\n", encoding="ascii")


def leer_cabecera_ply(origen: pathlib.Path) -> dict[str, int]:
    """Los recuentos que el PLY declara. Es de donde D23 los cuenta."""
    recuentos: dict[str, int] = {}
    with origen.open(encoding="ascii") as fichero:
        for linea in fichero:
            if linea.startswith("element "):
                _, nombre, cantidad = linea.split()
                recuentos[nombre] = int(cantidad)
            elif linea.strip() == "end_header":
                break
    return recuentos
