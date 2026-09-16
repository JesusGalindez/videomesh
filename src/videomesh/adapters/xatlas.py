"""El cortador y empaquetador del atlas — encargo 04, C2.

Proveedor elegido y declarado: **xatlas**, que es el que el encargo nombra. Corta
la malla en piezas por costuras de distorsion y las empaqueta en el cuadrado
unidad. No es un generador: lo unico que produce son dos numeros por vertice, y
**no mueve ni un vertice** — los parte, que es otra cosa y se cuenta aparte—.

Tres cosas que este modulo hace y conviene saber por que:

`padding` es el margen entre islas, en texeles, y es un parametro de la etapa y no
una constante escondida: sin margen las islas se tocan, y al filtrar la textura el
borde de una se mancha con el color de la vecina. El encargo lo trata como parametro
(F1 aconseja «sube el margen»), asi que viaja al informe con su valor.

`max_iterations` es cuanto se insiste en mejorar el corte. Mas iteraciones dan
menos islas y mas tiempo, y el numero se publica porque cambia el resultado.

Los vertices que salen son **mas** que los que entran, y es la unica medida de esta
etapa que puede parecer una perdida y no lo es: una costura obliga a que el mismo
vertice tenga dos coordenadas de textura distintas, asi que se duplica. La
superficie no cambia —misma posicion, mismos triangulos— y eso lo comprueba la
distancia de superficie en las dos direcciones, no una promesa.
"""

import importlib.metadata
import importlib.util
from dataclasses import dataclass
from typing import Any

from videomesh.domain.errores import ProveedorNoDisponible

__all__ = [
    "Atlas",
    "INSTALACION",
    "ITERACIONES_POR_DEFECTO",
    "MARGEN_POR_DEFECTO",
    "PROVEEDOR",
    "cortar_y_empaquetar",
    "exigir",
    "instalado",
    "version",
]

PROVEEDOR = "xatlas"

INSTALACION = "uv pip install 'videomesh[malla]'"

#: Margen entre islas, en texeles. Dos y no cero: con las islas pegadas, el filtrado
#: de la textura mezcla el borde de una con el fondo de la vecina.
MARGEN_POR_DEFECTO = 2

#: Cuanto insiste el cortador en mejorar sus costuras. Es el valor por defecto del
#: proveedor, declarado aqui para que el informe diga siempre con cual se hizo.
ITERACIONES_POR_DEFECTO = 1


def instalado() -> bool:
    """Se pregunta por el modulo, no se importa: `doctor` no puede depender de esto."""
    return importlib.util.find_spec(PROVEEDOR) is not None


def version() -> str:
    """La version instalada, que entra en el hash de entrada de la etapa (§9)."""
    try:
        return importlib.metadata.version(PROVEEDOR)
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover - sin instalar
        return "no instalado"


def exigir() -> None:
    """Falla antes de tocar un byte, diciendo que falta, para que y como se instala."""
    if instalado():
        return
    raise ProveedorNoDisponible(
        f"falta `{PROVEEDOR}`, que hace falta para cortar y empaquetar el atlas de UV.\n"
        f"  se instala con: {INSTALACION}\n"
        "  `videomesh doctor` dice el resto del entorno de una vez"
    )


@dataclass(frozen=True)
class Atlas:
    """Lo que el cortador produce, con los nombres que usa el informe."""

    #: Los vertices del atlas: **mas** que los de entrada, uno por lado de costura.
    vertices: Any
    triangulos: Any
    uv: Any
    #: Cuantas piezas tiene el atlas. No es un veredicto: es el resultado del corte.
    islas: int
    #: Ancho y alto de la rejilla en la que el empaquetado coloco las islas.
    empaquetado: tuple[int, int]


def cortar_y_empaquetar(
    origen: Any, *, margen: int = MARGEN_POR_DEFECTO, iteraciones: int = ITERACIONES_POR_DEFECTO
) -> Atlas:
    """Corta la malla en islas y las empaqueta, sin mover un vertice.

    Los parametros se validan con sus dos lados: un margen negativo no es «cero» y
    un numero de iteraciones negativo no es una malla distinta. Fingirlo produciria
    un informe que describe una ejecucion que nadie hizo.
    """
    from videomesh.adapters import pymeshlab

    exigir()
    if margen < 0:
        raise ValueError(f"el margen se cuenta en texeles y no puede ser negativo: {margen}")
    if iteraciones < 0:
        raise ValueError(f"las iteraciones no pueden ser negativas: {iteraciones}")

    import numpy as np
    import xatlas

    vertices, caras = pymeshlab.a_arreglos(origen)

    atlas = xatlas.Atlas()
    atlas.add_mesh(vertices, caras)

    corte = xatlas.ChartOptions()
    corte.max_iterations = iteraciones
    empaquetado = xatlas.PackOptions()
    empaquetado.padding = margen
    atlas.generate(corte, empaquetado)

    # `get_mesh` devuelve a que vertice de entrada corresponde cada uno de salida:
    # las posiciones se **leen**, no se recalculan, y por eso partir no puede mover.
    indice, indices, uv = atlas.get_mesh(0)
    return Atlas(
        vertices=np.asarray(vertices)[np.asarray(indice)],
        triangulos=np.asarray(indices, dtype="<u4"),
        uv=np.asarray(uv, dtype="<f4"),
        islas=int(atlas.chart_count),
        empaquetado=(int(atlas.width), int(atlas.height)),
    )
