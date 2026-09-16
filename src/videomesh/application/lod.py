"""La cadena de LODs — encargo 04, E2. Cada nivel se decima **del anterior**.

El encargo pide una cadena de niveles «cada uno decimado del anterior», y esa frase
es la etapa entera: no son tres decimados independientes de la maestra, es
192 → 96 → 48. Si el nivel 2 saliera de la maestra otra vez, su distancia contra el
nivel 1 no contaría el detalle que ese nivel ya perdió, y la cadena mentiría sobre
lo que se pierde al bajar.

Lo que publica, nivel a nivel:

```text
triangulos, de quien sale (entrada) y sus dos distancias      lo que produjo
la distancia contra la malla medida, en cada nivel            el freno del bucle (F2)
la silueta, comparada por el vecino contra la maestra         su auditoria
```

La silueta es donde un LOD se nota, y la compara el vecino contra la maestra — con
`lodSilhouetteMax` declarado en el destino cuando el asset trae niveles. Lo que esta
etapa no hace es juzgar si el nivel sirve para el juego: eso es su auditoría.
"""

import pathlib
import time
from typing import Any

from videomesh.adapters import pymeshlab
from videomesh.application import decimado
from videomesh.application.etapas import medir_distancia, memoria_maxima_mb
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
    directorio_de_etapa,
    escribir_informe,
    leer_informe,
    malla_de_la_etapa,
    salida_de,
)
from videomesh.project.procedencia import anotar_procedencia
from videomesh.project.stages import registrar_stage, ultima_de
from videomesh.project.store import abrir_proyecto

__all__ = ["ETAPA", "NIVEL", "encadenar"]

ETAPA = "lod"

PRODUCTOR = "videomesh/lod"

#: El nombre del fichero de un nivel. Los ficheros van de 1 en adelante, y `entrada`
#: dice de quién salió cada uno — `maestra` para el primero, `nivel-1` para el segundo.
NIVEL = "nivel-{n}.ply"

_IDENTIDAD = NIVEL.replace(".ply", "")


def encadenar(
    proyecto: pathlib.Path,
    *,
    niveles: list[int],
    herramienta: pathlib.Path | None = None,
) -> pathlib.Path:
    """Encadena los niveles, cada uno decimado del anterior. Devuelve su informe.

    Un nivel que no baja del anterior **para la cadena**: seguir encadenando con
    niveles que no bajan produciría una cadena que parece escalable y no lo es — la
    regla de F2 en miniatura. Lo que ya se produjo queda publicado, con el motivo.
    """
    ruta = pathlib.Path(proyecto)
    abrir_proyecto(ruta)
    pymeshlab.exigir()

    etapa_de_la_malla, _ = malla_de_trabajo_de(ruta)
    # La entrada de la cadena es lo que el decimado **publicó** como su salida: el
    # nivel 1 se decima de esa malla. Lo declara el informe — no se rehashea.
    salida_del_decimado = salida_de(ruta, decimado.ETAPA)
    if salida_del_decimado is None:
        raise ErrorDeProyecto(
            "no hay malla decimada de la que encadenar: la cadena de niveles sale de la "
            "malla de trabajo, y sin ella no hay de dónde bajar"
        )
    sha_de_la_entrada = str(salida_del_decimado["sha256"])

    parametros: dict[str, Any] = {"niveles": niveles}
    huella = hash_de_entrada(
        entradas=[sha_de_la_entrada],
        parametros=parametros,
        proveedor=pymeshlab.PROVEEDOR,
        version_del_proveedor=pymeshlab.version(),
    )

    anterior = ultima_de(ruta, ETAPA)
    falta_lo_producido = leer_informe(ruta, ETAPA) is None or any(
        not (directorio_de_etapa(ruta, ETAPA) / NIVEL.format(n=n + 1)).is_file()
        for n in range(len(niveles))
    )
    if not falta_lo_producido and not hay_que_reejecutar(anterior, hash_de_entrada=huella):
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
    directorio = directorio_de_etapa(ruta, ETAPA)
    directorio.mkdir(parents=True, exist_ok=True)
    salidas: list[dict[str, Any]] = []
    niveles_medidos: list[dict[str, Any]] = []

    for numero, objetivo in enumerate(niveles, start=1):
        # El nivel sale del **anterior**: la maestra solo produce el nivel 1.
        if numero == 1:
            entrada = decimado.malla_de_entrada(ruta)
            nombre_entrada = "maestra"
        else:
            nombre_anterior = NIVEL.format(n=numero - 1)
            entrada = directorio / nombre_anterior
            nombre_entrada = _IDENTIDAD.format(n=numero - 1)
            if not entrada.is_file():
                raise ErrorDeProyecto(
                    f"la cadena pide el nivel {numero} y su entrada {nombre_anterior} no "
                    "está: la cadena se cortó antes"
                )

        # No baja: la cadena para aquí, con lo que ya produjo. Simular los niveles
        # que faltan sería una cadena que parece escalable y no lo es.
        if pymeshlab.medir(entrada).caras <= objetivo:
            break

        destino = directorio / NIVEL.format(n=numero)
        _, _ = pymeshlab.decimar(entrada, destino, objetivo=objetivo)
        despues = pymeshlab.medir(destino)
        medida = describir_malla(destino, identidad=_IDENTIDAD.format(n=numero))
        salidas.append(medida)

        # Las dos distancias de siempre: lo que costó bajar de entrada, y lo que se
        # ha perdido desde el objeto de verdad — el freno del bucle (F2).
        distancia = medir_distancia(entrada, destino, herramienta=herramienta)
        distancia_medida = medir_distancia(malla_importada(ruta), destino, herramienta=herramienta)
        niveles_medidos.append(
            {
                "nivel": numero,
                "triangulos": despues.caras,
                "vertices": despues.vertices,
                "entrada": nombre_entrada,
                "distancia": distancia,
                "distancia_contra_la_malla_medida": distancia_medida,
                "memoria_maxima_mb": memoria_maxima_mb(),
            }
        )
        anotar_procedencia(
            ruta,
            Procedencia(
                etapa=ETAPA,
                artefacto=_IDENTIDAD.format(n=numero),
                estado=EstadoDeProcedencia.SIMPLIFICADO,
                productor=PRODUCTOR,
                version_del_productor=pymeshlab.version(),
                package_id=None,
                fuente=str(directorio),
                ruta_del_artefacto=NIVEL.format(n=numero),
                sha256_del_artefacto=str(medida["sha256"]),
                maquina=None,
            ),
        )

    duracion = time.monotonic() - empezado
    parada = len(niveles_medidos) < len(niveles)
    salida_de_referencia = salidas[0] if salidas else {"sha256": "sin-niveles"}

    registrar_stage(
        ruta,
        EjecucionDeStage(
            stage=ETAPA,
            estado=EstadoDeStage.COMPLETE,
            hash_de_entrada=huella,
            hash_de_salida=str(salida_de_referencia["sha256"]),
            determinismo=Determinismo.DETERMINISTA,
            proveedor=pymeshlab.PROVEEDOR,
            version_del_proveedor=pymeshlab.version(),
            duracion_s=duracion,
        ),
    )

    return escribir_informe(
        ruta,
        ETAPA,
        {
            "estado": EstadoDeStage.COMPLETE.value,
            "parametros": parametros,
            "entradas": [{"etapa": etapa_de_la_malla, "sha256": sha_de_la_entrada}],
            "salidas": salidas,
            "medidas": {
                "niveles": niveles_medidos,
                "cadena_parada": parada,
                "motivo_de_la_parada": (
                    "un objetivo no bajaba del nivel anterior: la cadena se detiene antes "
                    "de simular niveles que no escalan"
                    if parada
                    else None
                ),
                "duracion_s": duracion,
            },
            "purely_reconstructed": True,
            "procedencia": {
                "estado": EstadoDeProcedencia.SIMPLIFICADO.value,
                "productor": PRODUCTOR,
                "version_del_productor": pymeshlab.version(),
            },
            "notas": [
                "cada nivel sale del anterior: la distancia entre niveles cuenta el "
                "detalle que ya se habia perdido, y la cadena no miente sobre lo que "
                "cuesta bajar",
                "un nivel que no baja del anterior para la cadena: simularlo seria una "
                "cadena que parece escalable y no lo es",
            ],
        },
    )


def malla_de_trabajo_de(proyecto: pathlib.Path) -> tuple[str, pathlib.Path]:
    """La malla de trabajo y su etapa, delegando en quien la elige.

    Va en una función aparte para que el módulo no dependa de cómo se elige: hoy es
    la decimada, y el día que la retopología corra será la suya.
    """
    from videomesh.application.trabajo import malla_de_trabajo

    return malla_de_trabajo(proyecto)
