"""La cadena de produccion: que etapa esta hecha, cual caduco y cual toca.

Empieza en el paquete que llega de Colab y sigue hacia el asset que se usa:

```text
densa        el paquete medido, importado de fuera
limpieza     se van los trozos flotantes, los triangulos nulos y los vertices sueltos
decimado     colapso de aristas hasta un objetivo, con la distancia publicada
retopologia  triangulos desordenados -> quads alineados      sin instrumento hoy
uv           corte y empaquetado del atlas, con el juicio del vecino
normales     el detalle que el decimado quito, de vuelta como mapa
material     declara el material que ata la pieza y sus mapas
textura      los fotogramas reales proyectados sobre la malla   sin instrumento hoy
```

Y la regla con la que se decide cada situacion, escrita una sola vez:

```text
HECHA            hay una ejecucion acabada y su entrada es la de ahora
CADUCADA         hay una ejecucion acabada, pero su entrada ya no es la de ahora
TOCA             no hay ejecucion acabada, y sus entradas ya estan
ESPERA           sus entradas todavia no estan: la etapa anterior no ha acabado
SIN_INSTRUMENTO  el proveedor que la etapa necesita no esta en esta maquina
```

`SIN_INSTRUMENTO` existe por el bloque C y conviene decir por que es un estado y no
un fallo. Los dos proveedores de retopologia que el encargo nombra no estan aqui y no
se pueden poner, y el encargo manda declararlo en vez de sustituirlo por otro que da
menos. Una etapa que no se puede hacer **se dice**, para que nadie la intente ni la
espere: mirarla en `status` tiene que bastar, sin lanzarla para descubrirlo.

Las etapas **caducan en silencio** —se rehace la limpieza con otro umbral y el
decimado que habia ya no describe esta malla—, y lo que decide no es el estado del
registro sino el hash de su entrada. Un COMPLETE cuya entrada cambio no esta hecho,
esta caducado, y decirlo es el trabajo de este modulo.

Los parametros de cada etapa se leen **de su ultimo informe** y no de los valores
por defecto: lo que hay que comparar es la entrada con la que esa ejecucion se
hizo, no la que se haria hoy. Cambiar el parametro y volver a ejecutar es otra
ejecucion, no una caducidad.

No ejecuta nada: `estado_de_la_cadena` dice como esta la cadena, y hacer algo con
eso es de quien llama —en el encargo 04, `videomesh next`—.
"""

import pathlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from videomesh.adapters import xatlas
from videomesh.application import (
    decimado,
    limpieza,
    material,
    normales,
    retopologia,
    textura,
    uv,
)
from videomesh.application.densa import ETAPA as DENSA
from videomesh.application.densa import digest_de_entrada as digest_de_la_densa
from videomesh.application.densa import manifest_de
from videomesh.domain.errores import ErrorDePaquete
from videomesh.domain.stage import EjecucionDeStage, EstadoDeStage
from videomesh.project.informe import leer_informe
from videomesh.project.procedencia import ultima_de_la_etapa
from videomesh.project.stages import ultima_de

__all__ = ["CADENA", "DEFECTOS_POR_DEFECTO", "Paso", "Situacion", "estado_de_la_cadena"]

#: Los mismos dos estados que en `domain/stage.py`: los unicos con algo detras.
_ACABADOS = (EstadoDeStage.COMPLETE, EstadoDeStage.CACHED)


class Situacion(Enum):
    """La verdad de una etapa en la cadena, que no es su estado de ejecucion."""

    HECHA = "HECHA"
    CADUCADA = "CADUCADA"
    TOCA = "TOCA"
    ESPERA = "ESPERA"
    SIN_INSTRUMENTO = "SIN_INSTRUMENTO"


@dataclass(frozen=True)
class Paso:
    """Una etapa y lo que se puede decir de ella ahora mismo."""

    etapa: str
    situacion: Situacion
    motivo: str


#: El orden de la cadena. Ni alfabetico ni casual: limpiar antes de decimar, porque
#: limpiar cambia lo que se decima.
CADENA: tuple[str, ...] = (
    DENSA,
    limpieza.ETAPA,
    decimado.ETAPA,
    retopologia.ETAPA,
    uv.ETAPA,
    normales.ETAPA,
    material.ETAPA,
    textura.ETAPA,
)

#: De que depende cada etapa para poder empezar. La retopologia pide la malla
#: decimada; la etapa de UV pide **una malla de trabajo**, y la elige: la
#: retopologizada si la hay, la decimada si no. Su hash de entrada es el de la malla
#: que leyo, asi que el dia que la retopologia corra el atlas caduca solo y se rehace
#: con la malla nueva — que es §9 funcionando y no una excepcion.
_DEPENDE_DE: dict[str, tuple[str, ...]] = {
    limpieza.ETAPA: (DENSA,),
    decimado.ETAPA: (limpieza.ETAPA,),
    retopologia.ETAPA: (decimado.ETAPA,),
    # La etapa de UV espera a que **haya una malla de trabajo**, que es lo que de
    # verdad lee: la elige entre las que esten hechas, y lo declara. Pedirle el
    # decimado seria pedirle la etapa que hoy existe y no la que necesita —cuando
    # C1 corra, la malla de trabajo sera la retopologizada y su hash de entrada
    # cambiara solo—. Limpiar es la etapa que produce la primera malla de trabajo.
    uv.ETAPA: (limpieza.ETAPA,),
    # El horneado se escribe **en el espacio de una UV**: sin atlas vigente el mapa
    # describiria una superficie que ya no es la suya, asi que depende del atlas y no
    # de la malla. Es la misma razon por la que su hash de entrada lleva los dos.
    normales.ETAPA: (uv.ETAPA,),
    # D1 proyecta los fotogramas sobre la pieza vestida: el material declara a
    # quien pinta, y la textura proyectada tendra que declararlo en su sitio.
    material.ETAPA: (normales.ETAPA,),
    textura.ETAPA: (material.ETAPA,),
}

#: Las etapas cuyo proveedor puede no estar, con la funcion que lo comprueba. Es una
#: consulta al PATH y nada mas: no abre el proyecto ni ejecuta una etapa.
_SIN_INSTRUMENTO: dict[str, Callable[[], str | None]] = {
    retopologia.ETAPA: retopologia.motivo_de_ausencia,
    textura.ETAPA: textura.motivo_de_ausencia,
}

#: Que parametros usa cada etapa cuando todavia no hay informe. No son los que se
#: comparan —eso lo dice el informe—, son los que se usarian al ejecutarla.
DEFECTOS_POR_DEFECTO: dict[str, dict[str, Any]] = {
    DENSA: {},
    limpieza.ETAPA: {"minimo_relativo": limpieza.MINIMO_RELATIVO_POR_DEFECTO},
    decimado.ETAPA: {},
    retopologia.ETAPA: {},
    uv.ETAPA: {
        "margen": xatlas.MARGEN_POR_DEFECTO,
        "iteraciones": xatlas.ITERACIONES_POR_DEFECTO,
        "destino": uv.DESTINO_POR_DEFECTO,
        "solape_maximo": uv.SOLAPE_MAXIMO_POR_DEFECTO,
    },
    normales.ETAPA: {
        "resolucion": normales.RESOLUCION_POR_DEFECTO,
        "pullpush": True,
        "destino": uv.DESTINO_POR_DEFECTO,
        "reposo": "vecino mas cercano sobre la malla medida",
    },
    material.ETAPA: {"destino": material.PRESET_POR_DEFECTO},
    textura.ETAPA: {},
}

_MOTIVOS: dict[str, tuple[str, str]] = {
    DENSA: (
        "no hay ningun paquete importado todavia",
        "la procedencia o el paquete importado ya no estan donde estaban",
    ),
    limpieza.ETAPA: ("no se ha limpiado nada todavia", "ya no hay malla importada que limpiar"),
    decimado.ETAPA: ("no se ha decimado nada todavia", "ya no hay malla limpia que decimar"),
    retopologia.ETAPA: (
        "no se ha retopologizado nada todavia",
        "ya no hay malla decimada que retopologizar",
    ),
    uv.ETAPA: ("no se ha cortado ningun atlas todavia", "ya no hay malla de trabajo que cortar"),
    normales.ETAPA: (
        "no se ha horneado ningun mapa de normales todavia",
        "ya no hay malla con atlas sobre la que hornear",
    ),
    material.ETAPA: (
        "no se ha declarado ningun material todavia",
        "ya no hay pieza con mapa que vestir",
    ),
    textura.ETAPA: (
        "no se ha proyectado ningun fotograma todavia",
        "ya no hay material sobre el que proyectar",
    ),
}


def _digest_de(proyecto: pathlib.Path, etapa: str, parametros: Mapping[str, Any]) -> str | None:
    """La entrada de ahora para esa etapa, con los parametros que se le pasen.

    Cada etapa sabe calcular la suya —la densa su paquete, la limpieza la malla
    importada, el decimado la malla limpia— y este modulo no necesita saber como.
    """
    if etapa == DENSA:
        return _digest_de_la_densa_importada(proyecto)
    if etapa == limpieza.ETAPA:
        return limpieza.digest_de_la_entrada(proyecto, parametros=dict(parametros))
    if etapa == decimado.ETAPA:
        return decimado.digest_de_la_entrada(proyecto, parametros=dict(parametros))
    if etapa == uv.ETAPA:
        return uv.digest_de_la_entrada(proyecto, parametros=dict(parametros))
    if etapa == normales.ETAPA:
        return normales.digest_de_la_entrada(proyecto, parametros=dict(parametros))
    if etapa == material.ETAPA:
        return material.digest_de_la_entrada(proyecto, parametros=dict(parametros))
    # La retopologia no llega aqui: sin proveedor no hay ejecucion que comparar, y
    # `_paso` la declara antes de preguntar por su hash.
    return None


def _digest_de_la_densa_importada(proyecto: pathlib.Path) -> str | None:
    """Lo que la densa lee hoy: el paquete que se importo, tal y como esta ahora."""
    anotada = ultima_de_la_etapa(proyecto, DENSA)
    if anotada is None:
        return None
    try:
        documento = manifest_de(pathlib.Path(anotada.fuente))
    except ErrorDePaquete:
        return None
    return digest_de_la_densa(documento)


def _paso(proyecto: pathlib.Path, etapa: str, hechas: Mapping[str, Situacion]) -> Paso:
    """La situacion de una etapa, con la regla escrita una sola vez."""
    instrumento = _SIN_INSTRUMENTO.get(etapa)
    if instrumento is not None:
        ausencia = instrumento()
        if ausencia is not None:
            return Paso(etapa, Situacion.SIN_INSTRUMENTO, ausencia)

    for anterior in _DEPENDE_DE.get(etapa, ()):
        if hechas.get(anterior) is not Situacion.HECHA:
            return Paso(etapa, Situacion.ESPERA, f"espera a que `{anterior}` este hecha")

    sin_registro, sin_entrada = _MOTIVOS[etapa]
    ultima: EjecucionDeStage | None = ultima_de(proyecto, etapa)
    if ultima is None:
        return Paso(etapa, Situacion.TOCA, sin_registro)
    if ultima.estado not in _ACABADOS:
        return Paso(etapa, Situacion.TOCA, f"la ultima ejecucion quedo en {ultima.estado.value}")

    informe = leer_informe(proyecto, etapa)
    if informe is None:
        return Paso(
            etapa,
            Situacion.CADUCADA,
            "hay ejecucion y no hay informe: no se sabe con que parametros se hizo",
        )
    parametros = informe.get("parametros") or DEFECTOS_POR_DEFECTO[etapa]
    actual = _digest_de(proyecto, etapa, parametros)
    if actual is None:
        return Paso(etapa, Situacion.CADUCADA, sin_entrada)
    if ultima.hash_de_entrada != actual:
        return Paso(etapa, Situacion.CADUCADA, "la entrada es otra: lo que hay describe otra cosa")
    return Paso(etapa, Situacion.HECHA, "vigente")


def estado_de_la_cadena(proyecto: pathlib.Path) -> tuple[Paso, ...]:
    """La cadena entera, etapa a etapa. No ejecuta nada."""
    proyecto = pathlib.Path(proyecto)
    hechas: dict[str, Situacion] = {}
    pasos = []
    for etapa in CADENA:
        paso = _paso(proyecto, etapa, hechas)
        hechas[etapa] = paso.situacion
        pasos.append(paso)
    return tuple(pasos)
