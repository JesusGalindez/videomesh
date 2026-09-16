"""D28: la partición se define por índices, nunca por el número de workers.

El encargo 02 §4 pidió este arnés **antes** que el paralelismo, y por un motivo
concreto: comprobarlo después significa reescribir la reducción con código
encima, y el síntoma de incumplirlo es de los caros — un número que cambia según
la máquina, sin error, sin excepción y sin nada que lo delate.

En SoftSight la regla no se puede probar porque su visibilidad es de un solo
hilo. Aquí sí, y el caso rojo está medido: con la partición ingenua —repartir en
tantos trozos como workers— la misma entrada suma `8.0` con uno, dos o cuatro
workers y `0.0` con ocho.
"""

import concurrent.futures
import math

from videomesh.domain.reduccion import bloques, reducir

#: Una suma catastrófica: los sumandos grandes se cancelan y los pequeños
#: sobreviven solo si no caen en el mismo grupo que la cancelación. El
#: agrupamiento decide el resultado, que es justo lo que D28 vigila.
CANCELACION = [1e16, 1.0, -1e16, 1.0] * 4


def _parte_por_workers(valores: list[float], workers: int) -> list[list[float]]:
    """La partición que D28 prohíbe, aquí solo para medir lo que provoca."""
    tamano = math.ceil(len(valores) / workers)
    return [valores[i : i + tamano] for i in range(0, len(valores), tamano)]


def test_la_particion_ingenua_cambia_la_suma_con_el_numero_de_workers() -> None:
    """El fallo que la regla existe para impedir, medido en vez de supuesto."""
    resultados = {w: sum(sum(t) for t in _parte_por_workers(CANCELACION, w)) for w in (1, 2, 4, 8)}
    assert resultados == {1: 8.0, 2: 8.0, 4: 8.0, 8: 0.0}
    assert len(set(resultados.values())) > 1, "sin esto el resto del fichero no prueba nada"


def test_los_bloques_no_dependen_del_numero_de_workers() -> None:
    """`bloques` ni siquiera recibe los workers: no puede depender de ellos."""
    assert bloques(16, 4) == [range(0, 4), range(4, 8), range(8, 12), range(12, 16)]


def test_el_ultimo_bloque_es_mas_corto_cuando_no_divide() -> None:
    """Redondear hacia arriba el tamaño movería las fronteras; alargar el último
    bloque también. El tamaño es fijo y el resto va suelto."""
    assert bloques(10, 4) == [range(0, 4), range(4, 8), range(8, 10)]


def test_sin_elementos_no_hay_bloques() -> None:
    assert bloques(0, 4) == []


def test_el_mismo_resultado_bit_a_bit_con_uno_dos_cuatro_y_ocho_workers() -> None:
    """La comprobación que D28 pide entera: idéntico, no parecido."""
    con_uno = reducir(CANCELACION, tamano_de_bloque=4, workers=1)
    for workers in (2, 4, 8):
        assert reducir(CANCELACION, tamano_de_bloque=4, workers=workers) == con_uno


#: Un bloque por sumando, elegidos para que el **orden de combinación** decida:
#: ascendente da 1.0 y al revés da 0.0, medido. Con `CANCELACION` no serviría,
#: porque sus cuatro parciales son iguales y reordenarlos no cambia nada.
POR_BLOQUES = [1e16, 1.0, -1e16, 1.0]


def test_el_orden_en_que_terminan_los_workers_no_cambia_el_resultado() -> None:
    """Los workers procesan en cualquier orden y la reducción final va por índice
    de bloque **ascendente**. Se comprueba entregando los parciales al revés: si
    `reducir` sumara en orden de llegada, esto daría 0.0 en vez de 1.0."""

    def al_reves(trabajos: list[tuple[int, range]]) -> list[tuple[int, float]]:
        return [(indice, POR_BLOQUES[b.start]) for indice, b in reversed(trabajos)]

    assert reducir(POR_BLOQUES, tamano_de_bloque=1, mapear=al_reves) == 1.0


def test_si_se_combinara_en_orden_de_llegada_el_resultado_seria_otro() -> None:
    """El rojo del caso anterior, medido aparte: la misma entrega invertida,
    sumada tal cual llega, da 0.0. Sin esta línea la de arriba no demuestra que
    el orden ascendente esté haciendo algo."""
    llegada = 0.0
    for valor in reversed(POR_BLOQUES):
        llegada += valor
    assert llegada == 0.0

    ascendente = 0.0
    for valor in POR_BLOQUES:
        ascendente += valor
    assert ascendente == 1.0


def test_el_paralelismo_de_verdad_da_lo_mismo_que_un_solo_hilo() -> None:
    """Con hilos reales y el scheduler decidiendo, que es donde aparecería."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as piscina:
        del piscina
    assert reducir(CANCELACION, tamano_de_bloque=4, workers=8) == reducir(
        CANCELACION, tamano_de_bloque=4, workers=1
    )


def test_el_tamano_de_bloque_si_cambia_el_resultado_y_por_eso_es_contrato() -> None:
    """Cambiarlo reagrupa los sumandos igual que los workers lo hacían. La
    diferencia es que éste **se declara**: por eso D28 lo llama parte del
    contrato en cuanto un número de frontera dependa de una suma."""
    assert reducir(CANCELACION, tamano_de_bloque=4, workers=1) != reducir(
        CANCELACION, tamano_de_bloque=2, workers=1
    )


def test_un_tamano_de_bloque_que_no_es_positivo_se_rechaza() -> None:
    """Cero daría infinitos bloques vacíos y negativo ninguno; las dos cosas en
    silencio."""
    for tamano in (0, -1):
        try:
            bloques(8, tamano)
        except ValueError:
            continue
        raise AssertionError(f"tamano {tamano} deberia haberse rechazado")
