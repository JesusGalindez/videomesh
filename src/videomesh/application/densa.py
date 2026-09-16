"""La etapa `densa`: el paquete que llega de Colab — encargo 04, bloque A.

La densa exige CUDA y ninguna maquina de casa la tiene, asi que **llega de
fuera**: la produce un cuaderno en Colab y entra por aqui. Eso decide todo lo
demas, porque lo que entra es producto de un proveedor no determinista, de otra
maquina y de otra version.

Que hace, y en este orden:

```text
1  el manifest valida contra el esquema publicado de SoftSight (D15)
2  el paquete esta SEALED — consumir uno a medias es de D29
3  cada artifact resuelve dentro del paquete y pesa y hashea lo que declara (D6, V8)
4  se registra la etapa: COMPLETE, NON_DETERMINISTIC_PROVIDER, y de que maquina salio
```

Y lo que **no** hace: no recalcula la geometria. El paquete ya viene sellado, y
volver a medirlo produciria una segunda medida de lo mismo que acabaria
discrepando de la primera sin que nadie sepa cual manda. Tampoco copia el blob:
300 MB viajan por ruta (D1), no por dentro del proyecto.

El paso 3 es el que justifica la etapa entera. Un paquete que viajo por la red y
llego con un byte cambiado tiene que morir **aqui**, nombrando el artifact, y no
tres etapas mas tarde cuando el sintoma sea una malla con un pico.
"""

import hashlib
import json
import pathlib
import time
from typing import Any

from pydantic import ValidationError

from videomesh.contracts.modelos.reconstruction_package import ReconstructionPackage
from videomesh.domain.errores import (
    ErrorDePaquete,
    ManifestNoValido,
    PaqueteSinSellar,
    ProcedenciaIncompleta,
    SinSuperficie,
)
from videomesh.domain.procedencia import EstadoDeProcedencia, Procedencia
from videomesh.domain.project import CicloDeVida, Proyecto
from videomesh.domain.stage import Determinismo, EjecucionDeStage, EstadoDeStage
from videomesh.project.informe import escribir_informe
from videomesh.project.package import comprobar_integridad, comprobar_rutas
from videomesh.project.procedencia import anotar_procedencia
from videomesh.project.stages import registrar_stage
from videomesh.project.store import abrir_proyecto, guardar_proyecto

__all__ = [
    "CLAVE_DE_MAQUINA",
    "ETAPA",
    "MALLA",
    "artefacto_de_malla",
    "digest_de_entrada",
    "importar_paquete",
    "manifest_de",
    "maquina_declarada",
]

#: El nombre del stage. Uno solo, y escrito una sola vez.
ETAPA = "densa"

MANIFEST = "manifest.json"

#: El artefacto del que cuelga toda la cadena de acabado.
MALLA = "TRIANGLE_MESH"

#: Donde puede declarar el manifiesto la maquina. `extensions` existe para esto:
#: el esquema del paquete no tiene campo para ella y no se le anade uno desde
#: aqui — la frontera la mueve quien la publica.
CLAVE_DE_MAQUINA = "videomesh.procedencia.maquina"


def manifest_de(paquete: pathlib.Path) -> dict[str, Any]:
    """Lee el manifest de un paquete. Publica porque `status` tambien lo lee."""
    ruta = pathlib.Path(paquete) / MANIFEST
    if not ruta.is_file():
        raise ErrorDePaquete(f"en {paquete} no hay ningun {MANIFEST}: ahi no hay un paquete")
    documento: dict[str, Any] = json.loads(ruta.read_text(encoding="utf-8"))
    return documento


def _validar(documento: dict[str, Any]) -> ReconstructionPackage:
    """El esquema publicado, no una idea de lo que el manifest deberia decir."""
    try:
        return ReconstructionPackage.model_validate(documento)
    except ValidationError as error:
        detalles = "; ".join(
            f"{'.'.join(str(parte) for parte in fallo['loc']) or '(raiz)'}: {fallo['msg']}"
            for fallo in error.errors()
        )
        raise ManifestNoValido(
            f"el manifest no valida contra el esquema publicado de SoftSight: {detalles}. "
            "Se arregla en quien lo escribe, no aqui"
        ) from error


def artefacto_de_malla(documento: dict[str, Any]) -> dict[str, Any]:
    """El artifact de superficie del paquete, o dice que no hay ninguno.

    Sin malla no hay nada que limpiar, y saberlo en la etapa 1 en vez de en la 3
    es la diferencia entre un error util y tres etapas de trabajo perdido.
    """
    for artifact in documento["artifacts"]:
        if artifact["type"] == MALLA:
            entrada: dict[str, Any] = artifact
            return entrada
    tipos = ", ".join(sorted({str(artifact["type"]) for artifact in documento["artifacts"]}))
    raise SinSuperficie(
        f"el paquete {documento['packageId']!r} no trae ningun {MALLA}, solo {tipos}: "
        "no hay superficie que limpiar ni que decimar"
    )


def maquina_declarada(documento: dict[str, Any]) -> str | None:
    """La maquina, si el manifiesto la trae en `extensions`. Si no, `None` y se pide."""
    extensiones = documento.get("extensions") or {}
    extension = extensiones.get(CLAVE_DE_MAQUINA) or {}
    datos = extension.get("data") or {}
    declarada = datos.get("maquina")
    return str(declarada) if declarada else None


def digest_de_entrada(documento: dict[str, Any]) -> str:
    """Lo que la etapa densa **lee**, resumido: la identidad y lo que el paquete declara.

    Se calcula sobre lo declarado —`packageId` y la lista de artifacts con su
    tamano y su hash—, que es lo que cambia cuando llega otra densa. Es lo que
    decide si la etapa sigue vigente o esta caducada, y tiene que poder calcularse
    sin leer 300 MB de malla cada vez que alguien mira el proyecto.
    """
    lineas = [f"packageId {documento['packageId']}"]
    lineas += [
        f"{artifact['id']} {artifact['path']} {artifact['bytes']} {artifact['sha256']}"
        for artifact in documento["artifacts"]
    ]
    return hashlib.sha256("\n".join(lineas).encode("utf-8")).hexdigest()


def _proveedor_de(productor: str) -> str:
    """`producers/colmap · las 8 vistas registradas` -> `colmap`.

    El registro del stage quiere un identificador estable con el que se pueda
    agrupar, y la descripcion que el productor se pega detras no lo es: cambia con
    el numero de vistas. El nombre entero no se pierde —va a la procedencia, que
    es donde cabe—, asi que aqui se normaliza y alli se conserva.
    """
    sin_descripcion = productor.split("·", 1)[0].strip()
    return sin_descripcion.rsplit("/", 1)[-1].strip() or sin_descripcion


def _sha256_del_fichero(ruta: pathlib.Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def importar_paquete(
    proyecto: pathlib.Path, fuente: pathlib.Path, *, maquina: str | None = None
) -> pathlib.Path:
    """Registra un paquete producido fuera como la salida de un stage `densa`.

    No lo reejecuta: lo **comprueba**. Devuelve la ruta del informe que publica.
    """
    ruta = pathlib.Path(proyecto)
    abrir_proyecto(ruta)
    paquete = pathlib.Path(fuente)

    documento = manifest_de(paquete)
    validado = _validar(documento)

    if validado.state != "SEALED":
        raise PaqueteSinSellar(
            f"el paquete {validado.packageId!r} esta en {validado.state}, y un paquete que se "
            "esta escribiendo no se consume (D29): espera a que se selle"
        )

    comprobar_rutas(paquete, documento["artifacts"])
    comprobar_integridad(paquete, documento["artifacts"])
    malla = artefacto_de_malla(documento)

    de_donde = maquina or maquina_declarada(documento)
    if not de_donde:
        raise ProcedenciaIncompleta(
            f"no se sabe de que maquina salio {validado.packageId!r}, y dos densas de dos "
            "maquinas no son comparables. Declarala con `--maquina <nombre>` o en el "
            f"manifiesto, en extensions.{CLAVE_DE_MAQUINA}"
        )

    empezado = time.monotonic()
    entrada = digest_de_entrada(documento)
    salida = _sha256_del_fichero(paquete / MANIFEST)

    registrar_stage(
        ruta,
        EjecucionDeStage(
            stage=ETAPA,
            estado=EstadoDeStage.COMPLETE,
            hash_de_entrada=entrada,
            hash_de_salida=salida,
            # El determinismo de verdad: la misma entrada puede dar otra salida,
            # asi que el `resume` no se salta volver a comprobarlo.
            determinismo=Determinismo.NO_DETERMINISTA,
            proveedor=_proveedor_de(validado.producer.name),
            version_del_proveedor=validado.producer.version,
            duracion_s=time.monotonic() - empezado,
        ),
    )

    anotar_procedencia(
        ruta,
        Procedencia(
            etapa=ETAPA,
            artefacto=str(malla["id"]),
            estado=EstadoDeProcedencia.RECONSTRUIDO,
            productor=validado.producer.name,
            version_del_productor=validado.producer.version,
            package_id=validado.packageId,
            fuente=str(paquete),
            ruta_del_artefacto=str(malla["path"]),
            sha256_del_artefacto=str(malla["sha256"]),
            maquina=de_donde,
        ),
    )

    informe = escribir_informe(
        ruta,
        ETAPA,
        {
            "estado": EstadoDeStage.COMPLETE.value,
            "parametros": {"maquina": de_donde},
            "entradas": [
                {
                    "id": artifact["id"],
                    "path": artifact["path"],
                    "bytes": artifact["bytes"],
                    "sha256": artifact["sha256"],
                }
                for artifact in documento["artifacts"]
            ],
            "salidas": [{"id": str(malla["id"]), "sha256": str(malla["sha256"])}],
            "medidas": {
                "artefactos": len(documento["artifacts"]),
                "vistas": len(documento.get("cameras") or []),
                "escala": str(documento["scale"]["status"]),
            },
            "procedencia": {
                "estado": EstadoDeProcedencia.RECONSTRUIDO.value,
                "productor": validado.producer.name,
                "version_del_productor": validado.producer.version,
                "maquina": de_donde,
            },
            # Lo que no se comprobo, y por que. Sin esto el silencio se lee como
            # que se comprobo todo.
            "no_comprobado": [
                {
                    "que": "geometria_de_la_malla",
                    "motivo": "el paquete ya viene sellado, y recalcularlo aqui seria una "
                    "segunda medida de lo mismo",
                }
            ],
        },
    )

    leido = abrir_proyecto(ruta)
    guardar_proyecto(
        ruta,
        Proyecto(
            nombre=leido.nombre,
            estado=CicloDeVida.ACTIVO,
            artifacts=tuple(dict.fromkeys([*leido.artifacts, "DENSE"])),
        ),
    )
    return informe
