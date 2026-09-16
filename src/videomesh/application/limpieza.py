"""La etapa `limpieza` — encargo 04, B1.

La densa de un objeto sale con trozos flotantes: la pared de detras, el suelo,
nubes que el fusionado no supo descartar. Tres operaciones, y **ninguna decide
donde va un vertice**:

```text
componentes conexos    se quedan los que superan un umbral de tamano RELATIVO
                       al mayor — nunca absoluto
triangulos nulos       area cero o aristas nulas
vertices sueltos       sin ninguna cara
```

Que ninguna mueva un vertice no es un detalle de estilo: es lo que permite seguir
declarando `SIMPLIFIED` y `purelyReconstructed: true`. En cuanto una etapa
recoloca geometria, esta reparando, y eso se declara distinto (§9 y D21).

Lo que publica: cuantos componentes habia y cuantos quedaron —si de 400 quedan 3,
alguien quiere enterarse—, cuantos triangulos y vertices se fueron, y la
**distancia de superficie contra la malla medida**, en las dos direcciones. Tirar
geometria es perder algo, y cuanto se perdio es un numero.
"""

import pathlib
import time
from typing import Any

from videomesh.adapters import pymeshlab
from videomesh.application.etapas import medir_distancia, memoria_maxima_mb
from videomesh.domain.errores import ErrorDePaquete
from videomesh.domain.procedencia import EstadoDeProcedencia, Procedencia
from videomesh.domain.stage import (
    Determinismo,
    EjecucionDeStage,
    EstadoDeStage,
    hash_de_entrada,
    hay_que_reejecutar,
)
from videomesh.project.informe import (
    INFORME,
    describir_malla,
    escribir_informe,
    malla_de_la_etapa,
)
from videomesh.project.procedencia import anotar_procedencia, ultima_de_la_etapa
from videomesh.project.stages import registrar_stage, ultima_de
from videomesh.project.store import abrir_proyecto

__all__ = [
    "ETAPA",
    "MINIMO_RELATIVO_POR_DEFECTO",
    "digest_de_la_entrada",
    "limpiar",
    "malla_importada",
    "sha_de_la_entrada",
]

ETAPA = "limpieza"

#: Se queda el componente que tenga al menos esta fraccion de las caras del mayor.
#: Uno por ciento: una pared de fondo suele ser un componente entero y no una
#: fraccion, y una mota de tres triangulos nunca llega. Declarado, y parametro.
MINIMO_RELATIVO_POR_DEFECTO = 0.01

PRODUCTOR = "videomesh/limpieza"


def malla_importada(proyecto: pathlib.Path) -> pathlib.Path:
    """La malla que importo la etapa `densa`, donde este.

    La fuente vive fuera del proyecto —los blobs viajan por ruta (D1)— y quien
    sabe donde es el registro de procedencia.
    """
    anotada = ultima_de_la_etapa(proyecto, "densa")
    if anotada is None:
        raise ErrorDePaquete(
            "no hay ninguna densa importada: la limpieza no tiene nada que limpiar. "
            "Importala antes con `videomesh import <proyecto> <paquete>`"
        )
    return pathlib.Path(anotada.fuente) / anotada.ruta_del_artefacto


def sha_de_la_entrada(proyecto: pathlib.Path) -> str | None:
    """El hash de lo que la etapa lee hoy, declarado por quien lo importo."""
    anotada = ultima_de_la_etapa(proyecto, "densa")
    return None if anotada is None else anotada.sha256_del_artefacto


def digest_de_la_entrada(proyecto: pathlib.Path, *, parametros: dict[str, Any]) -> str | None:
    """El hash de entrada con esos parametros, o `None` si todavia no hay entrada."""
    sha = sha_de_la_entrada(proyecto)
    if sha is None:
        return None
    return hash_de_entrada(
        entradas=[sha],
        parametros=parametros,
        proveedor=pymeshlab.PROVEEDOR,
        version_del_proveedor=pymeshlab.version(),
    )


def _no_comprobado(
    resultado: pymeshlab.Limpieza, distancia: dict[str, Any]
) -> list[dict[str, str]]:
    """Lo que esta etapa **no** miro, con su motivo. Una lista vacia es una afirmacion."""
    pendientes = []
    if resultado.caras_que_el_proveedor_no_cargo:
        pendientes.append(
            {
                "que": "caras_que_el_proveedor_no_cargo",
                "motivo": (
                    f"el PLY declara {resultado.caras_que_el_proveedor_no_cargo} caras mas de las "
                    "que el proveedor cargo: descarta al leer las de indice repetido sin avisar, y "
                    "quitarlas es cosa suya, no de esta etapa"
                ),
            }
        )
    if distancia["estado"] != "MEDIDA":
        pendientes.append(
            {
                "que": "distancia_de_superficie",
                "motivo": str(distancia.get("motivo", "sin motivo declarado")),
            }
        )
    return pendientes


def limpiar(
    proyecto: pathlib.Path,
    *,
    minimo_relativo: float = MINIMO_RELATIVO_POR_DEFECTO,
    herramienta: pathlib.Path | None = None,
) -> pathlib.Path:
    """Limpia la malla importada y publica lo que quito. Devuelve su informe."""
    ruta = pathlib.Path(proyecto)
    abrir_proyecto(ruta)
    pymeshlab.exigir()

    origen = malla_importada(ruta)
    parametros = {"minimo_relativo": minimo_relativo}
    huella = digest_de_la_entrada(ruta, parametros=parametros)
    assert huella is not None  # hay procedencia: `malla_importada` acaba de leerla

    anterior = ultima_de(ruta, ETAPA)
    if not hay_que_reejecutar(anterior, hash_de_entrada=huella):
        assert anterior is not None and anterior.hash_de_salida is not None
        registrar_stage(
            ruta,
            EjecucionDeStage(
                stage=ETAPA,
                estado=EstadoDeStage.CACHED,
                hash_de_entrada=huella,
                hash_de_salida=anterior.hash_de_salida,
                determinismo=Determinismo.DETERMINISTA,
                proveedor=pymeshlab.PROVEEDOR,
                version_del_proveedor=pymeshlab.version(),
                duracion_s=0.0,
            ),
        )
        return malla_de_la_etapa(ruta, ETAPA).parent / INFORME

    empezado = time.monotonic()
    destino = malla_de_la_etapa(ruta, ETAPA)
    resultado = pymeshlab.limpiar(origen, destino, minimo_relativo=minimo_relativo)
    salida = describir_malla(destino)
    duracion = time.monotonic() - empezado
    distancia = medir_distancia(origen, destino, herramienta=herramienta)

    registrar_stage(
        ruta,
        EjecucionDeStage(
            stage=ETAPA,
            estado=EstadoDeStage.COMPLETE,
            hash_de_entrada=huella,
            hash_de_salida=str(salida["sha256"]),
            determinismo=Determinismo.DETERMINISTA,
            proveedor=pymeshlab.PROVEEDOR,
            version_del_proveedor=pymeshlab.version(),
            duracion_s=duracion,
        ),
    )
    anotar_procedencia(
        ruta,
        Procedencia(
            etapa=ETAPA,
            artefacto="malla",
            estado=EstadoDeProcedencia.SIMPLIFICADO,
            productor=PRODUCTOR,
            version_del_productor=pymeshlab.version(),
            package_id=None,
            fuente=str(destino.parent),
            ruta_del_artefacto=destino.name,
            sha256_del_artefacto=str(salida["sha256"]),
            maquina=None,
        ),
    )

    return escribir_informe(
        ruta,
        ETAPA,
        {
            "estado": EstadoDeStage.COMPLETE.value,
            "parametros": parametros,
            "entradas": [{"etapa": "densa", "sha256": sha_de_la_entrada(ruta)}],
            "salidas": [salida],
            "medidas": {
                "vertices_antes": resultado.antes.vertices,
                "vertices_despues": resultado.despues.vertices,
                "vertices_quitados": resultado.vertices_quitados,
                "triangulos_antes": resultado.antes.caras,
                "triangulos_despues": resultado.despues.caras,
                "triangulos_quitados": resultado.triangulos_quitados,
                "triangulos_degenerados": resultado.triangulos_degenerados,
                "vertices_sueltos": resultado.vertices_sueltos,
                # Lo que el proveedor descarto al cargar y no dijo. Sin este numero, una
                # cara con un indice repetido desaparece sin que nadie se entere.
                "caras_que_el_proveedor_no_cargo": resultado.caras_que_el_proveedor_no_cargo,
                "componentes_antes": resultado.antes.componentes,
                "componentes_despues": resultado.despues.componentes,
                "componentes_quitados": resultado.componentes_quitados,
                "aristas_de_borde": resultado.despues.aristas_de_borde,
                "memoria_maxima_mb": memoria_maxima_mb(),
                "distancia": distancia,
                "duracion_s": duracion,
            },
            "purely_reconstructed": True,
            "procedencia": {
                "estado": EstadoDeProcedencia.SIMPLIFICADO.value,
                "productor": PRODUCTOR,
                "version_del_productor": pymeshlab.version(),
            },
            # Como se lee el numero, escrito donde esta el numero. `falta` mide la
            # superficie que ya no esta, y aqui gran parte de ella es lo que esta etapa
            # tiro a proposito: un trozo flotante a un metro del objeto da 1,0 —la
            # distancia a la que estaba— y no un metro de superficie perdida.
            "notas": [
                "la distancia `falta` incluye la superficie que esta etapa quito: dice a que "
                "distancia estaba lo que se fue, no cuanto se movio lo que queda"
            ],
            "no_comprobado": _no_comprobado(resultado, distancia),
        },
    )
