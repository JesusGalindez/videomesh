"""Reducción paralela determinista — D28.

La regla entera, que no es la que se supone:

```text
los bloques se definen por índices de entrada y un tamaño de bloque fijo,
nunca por el número de workers

los workers los procesan en cualquier orden
la reducción final va por índice de bloque ascendente
```

Fijar el orden de reducción **no basta** si la partición depende del número de
workers: cuatro workers dan cuatro trozos y ocho dan ocho, así que los sumandos
se agrupan distinto y la suma cambia aunque cada ejecución reduzca ordenada.
Medido con una entrada que se cancela: `8.0` con uno, dos o cuatro workers y
`0.0` con ocho.

Esto existe **antes** que el paralelismo a propósito, que es lo que pidió el
encargo 02 §4: escribirlo después significa reescribir la reducción con código
encima, y el síntoma de incumplirlo es un número que cambia según la máquina, sin
error y sin excepción.

**Aquí no se usa `math.fsum`.** Sería exacto, y con él el orden de combinación
dejaría de importar — la regla quedaría vacía y la prueba que la sujeta pasaría
sin mirar nada. El día que una frontera compartida pida exactitud, `fsum` es la
respuesta; hasta entonces lo que se garantiza es que **dos ejecuciones dan los
mismos bits**, que es lo que D28 pide.
"""

import concurrent.futures
from collections.abc import Callable, Sequence

__all__ = ["bloques", "reducir"]

#: Cómo se entregan los parciales: cada uno con el índice de su bloque, en
#: cualquier orden. Que sea un argumento es lo que permite comprobar el orden
#: ascendente sin depender de lo que decida el scheduler ese día.
Mapeador = Callable[[list[tuple[int, range]]], list[tuple[int, float]]]


def bloques(elementos: int, tamano: int) -> list[range]:
    """La partición, **por índices de entrada**. No recibe los workers, así que
    no puede depender de ellos: es la única forma de que no vuelva a hacerlo.

    El último bloque queda más corto cuando no divide. Redondear el tamaño hacia
    arriba o alargar el último movería las fronteras, que es lo mismo que cambiar
    la partición por otra vía.
    """
    if tamano <= 0:
        raise ValueError(f"el tamano de bloque es {tamano}: cero daria infinitos bloques vacios")
    return [
        range(inicio, min(inicio + tamano, elementos)) for inicio in range(0, elementos, tamano)
    ]


def _sumar(valores: Sequence[float], bloque: range) -> float:
    total = 0.0
    for indice in bloque:
        total += valores[indice]
    return total


def reducir(
    valores: Sequence[float],
    *,
    tamano_de_bloque: int,
    workers: int = 1,
    mapear: Mapeador | None = None,
) -> float:
    """La suma, idéntica bit a bit sea cual sea el número de workers.

    `tamano_de_bloque` **es parte del contrato** en cuanto un número de frontera
    compartida dependa de esta suma: cambiarlo reagrupa los sumandos igual que
    los workers lo hacían. La diferencia es que éste se declara.
    """
    trabajos = list(enumerate(bloques(len(valores), tamano_de_bloque)))

    if mapear is not None:
        parciales = mapear(trabajos)
    elif workers == 1:
        parciales = [(indice, _sumar(valores, bloque)) for indice, bloque in trabajos]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as piscina:
            futuros = {
                piscina.submit(_sumar, valores, bloque): indice for indice, bloque in trabajos
            }
            # `as_completed` devuelve en orden de llegada a propósito: los workers
            # procesan en cualquier orden y el índice viaja con cada parcial.
            parciales = [
                (futuros[futuro], futuro.result())
                for futuro in concurrent.futures.as_completed(futuros)
            ]

    total = 0.0
    for _, parcial in sorted(parciales):
        total += parcial
    return total
