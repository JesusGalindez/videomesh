"""El modelo de escala, y lo que rechaza — D9.

`status`, `source` e incertidumbre viajaban desde R0-A y no rechazaban nada: sin
un sitio donde declarar un presupuesto, la regla no tenia que contradecir y
«metros sobre una escala que nadie ha fijado» se colaba entera. Los presupuestos
son ese sitio.

**R0 solo comprueba que el presupuesto sea coherente con la escala.** Evaluarlo
contra lo medido es R9, y decirlo asi evita que alguien lea un paquete aceptado
como un paquete aprobado.
"""

from collections.abc import Mapping, Sequence
from typing import Any

__all__ = ["ErrorDeEscala", "comprobar_escala"]

Presupuesto = Mapping[str, Any]


class ErrorDeEscala(ValueError):
    """Dos campos del paquete no pueden ser ciertos a la vez.

    El fichero esta bien y el hash cuadra; lo que falla es lo que dice. Del otro
    lado esto es salida 20, y de ahi el espacio `SS-RECON`.
    """


def _lleva_escala(nombre: str) -> bool:
    """Si la magnitud presupuestada depende de la escala.

    Mil triangulos son mil en cualquier escala; medio metro de desviacion sobre
    una reconstruccion sin escala no significa nada. **El vocabulario que lo
    decide es de R9 y aqui no existe todavia**, asi que todo nombre cuenta como
    con escala: un nombre desconocido se trata como si la llevara, porque suponer
    que no es suponer a favor. Es el lado que el contrato ya eligio despues de
    intentarlo permisivo.
    """
    del nombre
    return True


def comprobar_escala(escala: Mapping[str, Any], presupuestos: Sequence[Presupuesto]) -> None:
    """Falla si algun presupuesto se contradice con la escala declarada."""
    estado = escala["status"]
    vistos: set[str] = set()

    for presupuesto in presupuestos:
        nombre = presupuesto["name"]
        if nombre in vistos:
            raise ErrorDeEscala(
                f"el presupuesto {nombre!r} esta declarado dos veces; el nombre identifica"
            )
        vistos.add(nombre)

        unidades = presupuesto["units"]
        unidad = presupuesto.get("unit")

        if unidades == "ABSOLUTE":
            if unidad is None:
                raise ErrorDeEscala(
                    f"SS-RECON-002: el presupuesto {nombre!r} es ABSOLUTE y no declara unidad; "
                    "un maximo absoluto sin unidad no se puede comparar con nada"
                )
            if estado != "ABSOLUTE" and _lleva_escala(nombre):
                raise ErrorDeEscala(
                    f"SS-RECON-001: el presupuesto {nombre!r} declara {presupuesto['max']} "
                    f"{unidad} sobre una escala {estado}; una medida absoluta sobre una "
                    "reconstruccion sin escala fijada no significa nada. O se fija la escala, "
                    "o el presupuesto va RELATIVE_TO_DIAGONAL"
                )
        elif unidades == "RELATIVE_TO_DIAGONAL":
            if unidad is not None:
                raise ErrorDeEscala(
                    f"SS-RECON-002: el presupuesto {nombre!r} es una fraccion de la diagonal y "
                    f"declara la unidad {unidad!r}; una fraccion no tiene unidad, y ponersela es "
                    "declarar una escala por la puerta de atras: el consumidor leeria "
                    f"«{presupuesto['max']} {unidad}» donde el productor quiso decir un porcentaje"
                )
        else:
            raise ErrorDeEscala(f"unidades de presupuesto desconocidas en {nombre!r}: {unidades!r}")
