"""La etapa `decimado` — encargo 04, B2. Aqui vive el numero del encargo entero.

Colapso de aristas por error cuadratico, con **objetivo de triangulos** y no una
fraccion: una fraccion esconde la cifra que importa, y el presupuesto de un
destino se declara en triangulos.

Lo que publica, y es lo que la hace auditable:

```text
triangulos antes y despues
la distancia de superficie contra la entrada, en las DOS direcciones
```

Esa segunda linea es el criterio de cierre: decimar es perder detalle, y cuanto se
perdio es un numero medible y no una impresion. Se mide con `diffMeshes` de
SoftSight y se publican las dos direcciones **por separado** —promediarlas
esconderia lo unico que interesa, que quitar superficie y anadirla son averias
distintas—.

La referencia es la malla **medida**, no la de la etapa anterior: es contra el
objeto de verdad contra lo que se juzga, y el freno del bucle del encargo F2. Un
decimado que baja triangulos cumpliendo el presupuesto y destruye el objeto se ve
aqui y en ningun otro sitio.
"""

import pathlib
import time
from typing import Any

from videomesh.adapters import pymeshlab
from videomesh.application.etapas import medir_distancia, memoria_maxima_mb
from videomesh.application.limpieza import ETAPA as LIMPIEZA
from videomesh.application.limpieza import malla_importada
from videomesh.domain.errores import ErrorDeProyecto
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
    leer_informe,
    malla_de_la_etapa,
    salida_de,
)
from videomesh.project.procedencia import anotar_procedencia
from videomesh.project.stages import registrar_stage, ultima_de
from videomesh.project.store import abrir_proyecto

__all__ = [
    "ETAPA",
    "digest_de_la_entrada",
    "malla_de_entrada",
    "sha_de_la_entrada",
]

ETAPA = "decimado"

PRODUCTOR = "videomesh/decimado"


def malla_de_entrada(proyecto: pathlib.Path) -> pathlib.Path:
    """La malla limpia, que es lo que se decima."""
    informe = leer_informe(proyecto, LIMPIEZA)
    if informe is None:
        raise ErrorDeProyecto(
            "no hay malla limpia: el decimado no tiene nada que decimar. "
            f"Ejecuta antes `videomesh {LIMPIEZA} <proyecto>`"
        )
    return malla_de_la_etapa(proyecto, LIMPIEZA)


def sha_de_la_entrada(proyecto: pathlib.Path) -> str | None:
    """El hash de la malla limpia, declarado por quien la escribio."""
    salida = salida_de(proyecto, LIMPIEZA)
    return None if salida is None else str(salida["sha256"])


def digest_de_la_entrada(proyecto: pathlib.Path, *, parametros: dict[str, Any]) -> str | None:
    """El hash de entrada con ese objetivo, o `None` si todavia no hay malla limpia."""
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
    distancia: dict[str, Any], distancia_medida: dict[str, Any]
) -> list[dict[str, str]]:
    """Lo que no se pudo medir, con su motivo. Una lista vacia es una afirmacion."""
    pendientes = []
    for nombre, medida in (
        ("distancia_de_superficie", distancia),
        ("distancia_contra_la_malla_medida", distancia_medida),
    ):
        if medida["estado"] != "MEDIDA":
            pendientes.append(
                {"que": nombre, "motivo": str(medida.get("motivo", "sin motivo declarado"))}
            )
    return pendientes


def decimar(
    proyecto: pathlib.Path,
    *,
    objetivo: int,
    herramienta: pathlib.Path | None = None,
) -> pathlib.Path:
    """Decima la malla limpia hasta `objetivo` triangulos. Devuelve su informe.

    La distancia se mide **contra la malla importada**, que es la medida, y no
    contra la limpia: limpiar ya tiro geometria, y mezclar las dos perdidas en un
    solo numero daria una cifra que no dice cuanto costo decimar.
    """
    ruta = pathlib.Path(proyecto)
    abrir_proyecto(ruta)
    pymeshlab.exigir()

    origen = malla_de_entrada(ruta)
    parametros = {"objetivo": objetivo}
    huella = digest_de_la_entrada(ruta, parametros=parametros)
    assert huella is not None  # hay malla limpia: `malla_de_entrada` acaba de leerla

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
    antes, despues = pymeshlab.decimar(origen, destino, objetivo=objetivo)
    salida = describir_malla(destino)
    duracion = time.monotonic() - empezado
    # Dos distancias, y las dos hacen falta:
    #  - contra la **entrada** de la etapa, que es lo que el encargo pide en B2: cuanto
    #    costo decimar.
    #  - contra la **malla medida**, que es el freno del bucle (F2): cuanto se ha
    #    perdido desde el objeto de verdad. Sin la segunda, un decimado que destruye
    #    el objeto pero cumple el presupuesto pasaria la puerta.
    distancia = medir_distancia(origen, destino, herramienta=herramienta)
    distancia_medida = medir_distancia(malla_importada(ruta), destino, herramienta=herramienta)

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
            "entradas": [{"etapa": LIMPIEZA, "sha256": sha_de_la_entrada(ruta)}],
            "salidas": [salida],
            "medidas": {
                "triangulos_antes": antes.caras,
                "triangulos_despues": despues.caras,
                "triangulos_quitados": antes.caras - despues.caras,
                "vertices_antes": antes.vertices,
                "vertices_despues": despues.vertices,
                "aristas_de_borde": despues.aristas_de_borde,
                "memoria_maxima_mb": memoria_maxima_mb(),
                "distancia": distancia,
                "distancia_contra_la_malla_medida": distancia_medida,
                "duracion_s": duracion,
            },
            "purely_reconstructed": True,
            "procedencia": {
                "estado": EstadoDeProcedencia.SIMPLIFICADO.value,
                "productor": PRODUCTOR,
                "version_del_productor": pymeshlab.version(),
            },
            # Sin distancia no hay veredicto posible sobre cuanto costo decimar, y
            # eso se declara aqui ademas de en su propio sitio: esta lista es la que
            # convierte un «no salio nada mal» en «esto no se miro».
            "no_comprobado": _no_comprobado(distancia, distancia_medida),
        },
    )
