"""El FrameGraph: ninguna transformacion se hornea sin registrarla — D11.

Cuatro marcos —CAMERA, RECONSTRUCTION, ASSET_CANONICAL, PRODUCTION— y cada arista
guardando origen, destino, matriz, motivo y productor.

Lo que convierte esto en registro no es que haya aristas declaradas, que se cumple
rellenando una lista, sino que **un marco al que no hay camino se rechaza**. Y el
camino se busca desde RECONSTRUCTION porque es donde estan los numeros: las cajas
y los volumenes salen del PLY, que viene en ese marco.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from videomesh.domain.algebra import IDENTIDAD, componer, es_rigida, inversa_rigida
from videomesh.domain.errores import ErrorDeContrato

__all__ = ["MARCOS", "MEDIDO_EN", "ErrorDeMarco", "comprobar_frame_graph", "resolver_marco"]

#: Los cuatro marcos del contrato. Uno que no este aqui no es un marco.
MARCOS = ("CAMERA", "RECONSTRUCTION", "ASSET_CANONICAL", "PRODUCTION")

#: Desde donde se busca camino: es donde se miden las cosas.
MEDIDO_EN = "RECONSTRUCTION"

Arista = Mapping[str, Any]


class ErrorDeMarco(ErrorDeContrato, ValueError):
    """El grafo de marcos no dice lo que hace falta para interpretar una medida."""


def comprobar_frame_graph(transformaciones: Sequence[Arista]) -> None:
    """Comprueba las aristas y que todo marco declarado sea alcanzable."""
    vistas: set[frozenset[str]] = set()
    declarados: set[str] = set()

    for arista in transformaciones:
        origen, destino = arista["from"], arista["to"]
        for marco in (origen, destino):
            if marco not in MARCOS:
                raise ErrorDeMarco(
                    f"MARCO_DESCONOCIDO: {marco!r}; los marcos son {', '.join(MARCOS)}"
                )
        if origen == destino:
            raise ErrorDeMarco(
                f"TRANSFORMACION_MAL_FORMADA: una arista de {origen} a si mismo no transforma nada"
            )
        salto = frozenset((origen, destino))
        if salto in vistas:
            raise ErrorDeMarco(
                f"TRANSFORMACION_MAL_FORMADA: el salto {origen} - {destino} esta declarado dos "
                "veces; el grafo ya se recorre en los dos sentidos, asi que la segunda es el "
                "mismo dato esperando a dejar de cuadrar"
            )
        vistas.add(salto)
        if not es_rigida(arista["matrix"]):
            raise ErrorDeMarco(
                f"TRANSFORMACION_NO_RIGIDA: la arista {origen} - {destino} lleva escala o "
                "proyeccion dentro, asi que ir y volver no devuelve el punto de partida"
            )
        declarados.update((origen, destino))

    if not declarados:
        return
    alcanzables = _alcanzables(transformaciones)
    perdidos = declarados - alcanzables
    if perdidos:
        raise ErrorDeMarco(
            f"MARCO_INALCANZABLE: {', '.join(sorted(perdidos))} no tiene camino desde "
            f"{MEDIDO_EN}, que es donde estan los numeros"
        )


def _alcanzables(transformaciones: Sequence[Arista]) -> set[str]:
    vecinos: dict[str, set[str]] = {}
    for arista in transformaciones:
        vecinos.setdefault(arista["from"], set()).add(arista["to"])
        vecinos.setdefault(arista["to"], set()).add(arista["from"])
    alcanzados = {MEDIDO_EN}
    pendientes = [MEDIDO_EN]
    while pendientes:
        actual = pendientes.pop()
        for vecino in vecinos.get(actual, ()):
            if vecino not in alcanzados:
                alcanzados.add(vecino)
                pendientes.append(vecino)
    return alcanzados


def resolver_marco(transformaciones: Sequence[Arista], origen: str, destino: str) -> list[float]:
    """La matriz que lleva del marco origen al destino, componiendo el camino.

    **No devuelve la identidad cuando no hay camino.** Suponer que dos marcos sin
    arista son el mismo es el error que D11 describe, no su arreglo.

    Las aristas se recorren en los dos sentidos: una transformacion rigida tiene
    inversa exacta, y declarar las dos direcciones seria el mismo dato dos veces.
    """
    if origen == destino:
        return list(IDENTIDAD)

    caminos: dict[str, list[float]] = {origen: list(IDENTIDAD)}
    pendientes = [origen]
    while pendientes:
        actual = pendientes.pop(0)
        for siguiente, salto in _saltos_desde(transformaciones, actual):
            if siguiente in caminos:
                continue
            caminos[siguiente] = componer(salto, caminos[actual])
            if siguiente == destino:
                return caminos[siguiente]
            pendientes.append(siguiente)

    raise ErrorDeMarco(
        f"MARCO_INALCANZABLE: no hay camino de {origen} a {destino}; "
        "sin arista no se puede suponer que sean el mismo marco"
    )


def _saltos_desde(transformaciones: Sequence[Arista], marco: str) -> list[tuple[str, list[float]]]:
    salidas = []
    for arista in transformaciones:
        if arista["from"] == marco:
            salidas.append((arista["to"], list(arista["matrix"])))
        elif arista["to"] == marco:
            salidas.append((arista["from"], inversa_rigida(arista["matrix"])))
    return salidas
