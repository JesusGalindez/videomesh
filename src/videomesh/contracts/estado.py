"""Lo que VideoMesh declara hablar, en bloque — D12.

«El consumidor comprueba el bloque, no un campo.» Siete numeros que por separado
existen pueden no haberse visto nunca juntos, y una constante suelta con la
version del paquete puede ser correcta **por casualidad**: el 2026-09-14
`reconstructionReport` subio de 0.1 a 0.2 despues de cambiar seis veces con el
numero quieto.

El registro de SoftSight —`contracts/versions.json`— **no se copia aqui**. Se lee
del original, como el contrato se lee por el symlink: una copia diverge. Lo que si
vive aqui, generado y commiteado, es `contracts/estado.json`, que es la
combinacion que este repositorio declara hablar. Declararla es lo que hace que
subir un numero alla y no regenerar aqui ponga la verificacion en rojo; leerla al
vuelo del original no declararia nada.
"""

import json
import pathlib
from collections.abc import Mapping, Sequence
from typing import Any

from videomesh.contracts.generacion import ESQUEMAS
from videomesh.contracts.serialization import volcar_json

__all__ = [
    "ESTADO",
    "ErrorDeCombinacion",
    "combinacion_declarada",
    "combinaciones_admitidas",
    "comprobar_combinacion",
    "estado_generado",
    "version_del_paquete",
]

#: El documento publicado. Lo escribe `scripts/generar_estado.py`.
ESTADO = pathlib.Path(__file__).resolve().parents[3] / "contracts" / "estado.json"

Combinacion = Mapping[str, Any]


class ErrorDeCombinacion(ValueError):
    """La combinacion declarada no es una de las que el consumidor ha visto."""


def _registro() -> dict[str, Any]:
    datos: dict[str, Any] = json.loads((ESQUEMAS / "versions.json").read_text(encoding="utf-8"))
    return datos


def combinaciones_admitidas() -> list[dict[str, Any]]:
    """Las combinaciones que SoftSight publica como vigentes. Hoy hay una."""
    return [
        {contrato["name"]: contrato["value"] for contrato in bloque}
        for bloque in _registro()["declared"]
    ]


def estado_generado() -> str:
    """El texto de `contracts/estado.json` tal y como sale del registro de hoy."""
    documento = {
        "documentType": "videomesh.contract-state",
        "$comment": (
            "Generado por scripts/generar_estado.py del registro de SoftSight. "
            "No se edita a mano: es lo que VideoMesh declara hablar, en bloque (D12)."
        ),
        "combinacion": combinaciones_admitidas()[-1],
    }
    return volcar_json(documento) + "\n"


def combinacion_declarada() -> dict[str, Any]:
    """La combinacion que este repositorio publica."""
    documento = json.loads(ESTADO.read_text(encoding="utf-8"))
    declarada: dict[str, Any] = documento["combinacion"]
    return declarada


def version_del_paquete() -> str:
    """`contractVersion` del paquete de reconstruccion, leida del bloque."""
    return str(combinacion_declarada()["reconstructionPackage"])


def comprobar_combinacion(declarada: Combinacion, admitidas: Sequence[Combinacion]) -> None:
    """Falla si la combinacion entera no es una de las admitidas.

    Recibe las dos como argumento a proposito: es lo que permite escribir el caso
    que la rompe sin tocar ningun fichero del repositorio.
    """
    if not admitidas:
        raise ErrorDeCombinacion("el registro no declara ninguna combinacion vigente")

    nombres = set(admitidas[0])
    faltan = nombres - set(declarada)
    if faltan:
        raise ErrorDeCombinacion(
            f"el bloque no declara {', '.join(sorted(faltan))}: "
            "faltar no es hablar menos, es no decir que se habla"
        )
    sobran = set(declarada) - nombres
    if sobran:
        raise ErrorDeCombinacion(
            f"el bloque declara {', '.join(sorted(sobran))}, que el registro no conoce"
        )

    if any(dict(declarada) == dict(admitida) for admitida in admitidas):
        return

    difieren = sorted(
        nombre
        for nombre in nombres
        if all(declarada[nombre] != admitida[nombre] for admitida in admitidas)
    ) or sorted(nombre for nombre in nombres if declarada[nombre] != admitidas[0][nombre])
    raise ErrorDeCombinacion(
        "esta combinacion no la ha declarado nadie; cada numero existe por separado "
        f"pero juntos no se han visto nunca. Difieren: {', '.join(difieren)}"
    )
