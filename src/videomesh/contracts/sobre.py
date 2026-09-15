"""El sobre de todo documento que sale de VideoMesh — D16.

Tres campos: `documentType`, `contractVersion` y `contractSchemaSha256`. Se
comprueban **en el escritor**, antes de que nada llegue a disco. Que los rechace
el consumidor llega tarde: para entonces el paquete ya esta escrito y sellado, y
la identidad de un paquete sellado no se reescribe, se publica otra.

El hash **no se copia a mano**. D16 reparte la autoridad en tres: el contrato
decide que versiones se aceptan, `contracts/*.schema.json` es el contrato legible
por maquina, y `contracts/registry.json` es la busqueda por hash. Aqui se lee de
los dos ultimos, asi que el dia que el esquema cambie el sobre cambia solo — y si
el registro no lo conoce, se para aqui en vez de producir un paquete que el otro
lado dejara en `UNSUPPORTED` con `ESQUEMA_NO_COINCIDE`.
"""

import hashlib
import json
from typing import Any

from videomesh.contracts.estado import version_del_paquete
from videomesh.contracts.generacion import ESQUEMAS
from videomesh.contracts.serialization import volcar_json

__all__ = ["PAQUETE_DE_RECONSTRUCCION", "ErrorDeSobre", "sobre_de", "volcar_documento"]

#: `documentType` del paquete de reconstruccion, que es lo que VideoMesh escribe.
PAQUETE_DE_RECONSTRUCCION = "videomesh.reconstruction-package"

#: Que esquema gobierna cada tipo de documento. Un nombre suelto como
#: `reconstruction` seria ambiguo y el contrato lo prohibe (D14).
ESQUEMA_DE = {PAQUETE_DE_RECONSTRUCCION: "reconstruction-package"}

_CAMPOS = ("documentType", "contractVersion", "contractSchemaSha256")


class ErrorDeSobre(ValueError):
    """El documento no declara contra que contrato se escribio. No sale del proceso."""


def _registro() -> dict[str, Any]:
    datos: dict[str, Any] = json.loads((ESQUEMAS / "registry.json").read_text(encoding="utf-8"))
    return datos


def _hash_del_esquema(nombre: str) -> str:
    ruta = ESQUEMAS / f"{nombre}.schema.json"
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def sobre_de(tipo_de_documento: str) -> dict[str, str]:
    """Devuelve el sobre de hoy para ese tipo de documento, leido del esquema."""
    if tipo_de_documento not in ESQUEMA_DE:
        raise ErrorDeSobre(f"documentType desconocido: {tipo_de_documento!r}")
    return {
        "documentType": tipo_de_documento,
        # Del bloque publicado, no del registro de esquemas: es la misma cifra en
        # dos sitios y D12 dice cual manda.
        "contractVersion": version_del_paquete(),
        "contractSchemaSha256": _hash_del_esquema(ESQUEMA_DE[tipo_de_documento]),
    }


def comprobar_sobre(documento: dict[str, Any]) -> None:
    """Falla si el documento no declara un sobre que el consumidor vaya a aceptar."""
    for campo in _CAMPOS[:2]:
        if not documento.get(campo):
            raise ErrorDeSobre(f"al documento le falta {campo}: sin el no se sabe que es")

    tipo = documento["documentType"]
    if tipo not in ESQUEMA_DE:
        raise ErrorDeSobre(f"documentType desconocido: {tipo!r}")

    registro = _registro()
    version = documento["contractVersion"]
    if version not in registro["contractVersions"]:
        aceptadas = ", ".join(registro["contractVersions"])
        raise ErrorDeSobre(f"contractVersion {version!r} no esta entre las aceptadas: {aceptadas}")

    # Opcional mientras el contrato este en DRAFT: sin el no se comprueba nada y se
    # dice. Si viene, tiene que estar registrado o el otro lado no lo interpreta.
    declarado = documento.get("contractSchemaSha256")
    if declarado is None:
        return
    if declarado not in {entrada["sha256"] for entrada in registro["schemas"]}:
        raise ErrorDeSobre(
            f"contractSchemaSha256 {declarado} no esta en el registro publicado; "
            "el consumidor lo dejaria en UNSUPPORTED con ESQUEMA_NO_COINCIDE"
        )


def volcar_documento(documento: dict[str, Any]) -> str:
    """Serializa un documento de la frontera. Sin sobre valido, no hay texto."""
    comprobar_sobre(documento)
    return volcar_json(documento)
