"""Cual es la malla con la que sigue la cadena — encargo 04, bloque C.

Hasta el bloque B la respuesta era facil y por eso no estaba escrita: cada etapa
leia la anterior. Con el bloque C deja de serlo, porque la retopologia esta
**declarada sin instrumento** (los dos proveedores que el encargo nombra no estan en
esta maquina) y la etapa de UV tiene que elegir entre las mallas que existen.

La regla, escrita una vez: **la malla de trabajo es la de la etapa mas avanzada que
este hecha**. Hoy eso es el decimado; el dia que haya proveedor de retopologia y su
etapa corra, la malla de trabajo sera la suya — y la etapa de UV no cambia: su hash
de entrada es el de la malla que leyo, asi que la suya caduca sola y se rehace con
la nueva. Eso es §9 funcionando y no una excepcion.

Se mide por **dos cosas**: que la ultima ejecucion acabase y que su informe exista.
Con una sola, un stage a medias pasaria por malla de trabajo y la etapa de arriba
publicaria un asset de algo que nadie termino.
"""

import pathlib

from videomesh.application import decimado, limpieza, retopologia
from videomesh.domain.errores import ErrorDeProyecto
from videomesh.domain.stage import EstadoDeStage
from videomesh.project.informe import leer_informe, malla_de_la_etapa
from videomesh.project.stages import ultima_de

__all__ = ["ETAPAS_DE_MALLA", "malla_de_trabajo"]

#: De la mas avanzada a la menos. El orden es la regla: la primera que este hecha.
ETAPAS_DE_MALLA: tuple[str, ...] = (retopologia.ETAPA, decimado.ETAPA, limpieza.ETAPA)

#: Los dos estados en los que hay una malla detras. Los mismos que en `cadena.py`.
_ACABADOS = (EstadoDeStage.COMPLETE, EstadoDeStage.CACHED)


def malla_de_trabajo(proyecto: pathlib.Path) -> tuple[str, pathlib.Path]:
    """La etapa que produjo la malla de trabajo, y su camino."""
    for etapa in ETAPAS_DE_MALLA:
        ultima = ultima_de(proyecto, etapa)
        if ultima is None or ultima.estado not in _ACABADOS:
            continue
        if leer_informe(proyecto, etapa) is None:
            continue
        return etapa, malla_de_la_etapa(proyecto, etapa)
    raise ErrorDeProyecto(
        "no hay malla de trabajo: limpia la malla medida antes de pedir un atlas. "
        f"Ninguna de estas etapas tiene una ejecucion acabada: {', '.join(ETAPAS_DE_MALLA)}"
    )
