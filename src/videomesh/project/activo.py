"""El manifiesto de produccion que esta cadena publica — encargo 04, bloque C.

`softsight.production-asset` **es del vecino**: su forma la fija su esquema, y este
repositorio genera su modelo desde ese mismo fichero
(`contracts/modelos/production_asset.py`, por D15). Aqui se **escribe validado**:
el documento se comprueba con ese modelo antes de tocar el disco, porque un
manifiesto que no encaja con el esquema se descubre en su puerta con un «no encaja»
que no dice que campo, y escribirlo mal es de este lado.

Es un modulo corto a proposito. Todo lo que un asset de produccion declara —perfiles,
LOD, colision, texturas— es de los bloques D y E; lo que hay aqui es lo minimo para
que el de este bloque **tenga juez**: una maestra en GLB, sus bytes y su hash, y un
destino que declare el unico tope que esta etapa promete cumplir.

`bytes` y `sha256` se leen del fichero y no se copian de lo que alguien creyo que
pesaba. Es la misma regla que el paquete de reconstruccion (V6, V8) y se repite en
vez de compartirse por lo mismo que el vecino repite su lector: aquel describe
artifacts con `type` y con `purelyReconstructed`, y estos llevan `role` y `format`.
Forzar un lector comun obligaria a que uno de los dos documentos tuviera campos del
otro.
"""

import hashlib
import pathlib
from collections.abc import Mapping, Sequence
from typing import Any

from videomesh.contracts.estado import version_del_paquete
from videomesh.contracts.modelos import ProductionAsset
from videomesh.contracts.serialization import volcar_json
from videomesh.domain.errores import ErrorDePaquete

__all__ = ["ACTIVO", "TIPO_DE_DOCUMENTO", "describir_artefacto", "escribir_activo"]

#: Donde se escribe el manifiesto dentro del directorio del asset.
ACTIVO = "asset.json"

#: El `documentType` del vecino: este documento no es de VideoMesh, es suyo.
TIPO_DE_DOCUMENTO = "softsight.production-asset"


def describir_artefacto(
    raiz: pathlib.Path,
    ruta: str | pathlib.Path,
    *,
    identidad: str,
    rol: str,
    formato: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Lee el fichero y devuelve su entrada del manifiesto, con `bytes` y `sha256`.

    La ruta se escribe **relativa a la raiz del asset**: una absoluta no viaja a
    ningun sitio, y su lector la rechaza por su nombre antes de abrir nada.
    """
    relativa = pathlib.PurePosixPath(pathlib.PurePath(ruta).as_posix())
    if relativa.is_absolute() or ".." in relativa.parts:
        raise ErrorDePaquete(
            f"el artefacto {identidad!r} quiere declarar {relativa}, que sale de la raiz del "
            "asset: un manifiesto que apunta fuera no se puede mover ni comprobar"
        )
    fichero = raiz / relativa
    if not fichero.is_file():
        raise ErrorDePaquete(f"el artefacto {identidad!r} apunta a {relativa}, que no existe")

    contenido = fichero.read_bytes()
    entrada: dict[str, Any] = {
        "id": identidad,
        "path": str(relativa),
        "bytes": len(contenido),
        "sha256": hashlib.sha256(contenido).hexdigest(),
        "role": rol,
    }
    if formato is not None:
        entrada["format"] = formato
    entrada.update(extra)
    return entrada


def escribir_activo(
    directorio: pathlib.Path,
    *,
    identidad: str,
    productor: str,
    artefactos: Sequence[Mapping[str, Any]],
    destino: Mapping[str, Any],
    version_del_productor: str | None = None,
    materiales: Sequence[Mapping[str, Any]] | None = None,
    derivacion: Mapping[str, Any] | None = None,
) -> pathlib.Path:
    """Escribe `asset.json` sellado, o falla sin escribir nada.

    La validacion es con el modelo del vecino y no con una lista de campos propia:
    si su esquema crece, esta puerta crece con el sin que nadie la toque.
    """
    documento: dict[str, Any] = {
        "documentType": TIPO_DE_DOCUMENTO,
        "contractVersion": version_del_paquete(),
        "assetId": identidad,
        "state": "SEALED",
        "producer": {"name": productor, "version": version_del_productor or version_del_paquete()},
        "artifacts": [dict(artefacto) for artefacto in artefactos],
        "target": dict(destino),
    }
    if materiales is not None:
        documento["materials"] = [dict(material) for material in materiales]
    if derivacion is not None:
        documento["derivation"] = dict(derivacion)

    # El modelo del vecino, y no una copia: `extra="forbid"` en su esquema es lo que
    # convierte un campo de mas en un rechazo suyo, y aqui se adelanta.
    ProductionAsset.model_validate(documento)

    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / ACTIVO
    ruta.write_text(volcar_json(documento) + "\n", encoding="utf-8")
    return ruta
