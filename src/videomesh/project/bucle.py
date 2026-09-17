"""Los intentos del bucle, en disco — bloque F del encargo 04.

Un fichero JSONL al lado del historial de stages y de la procedencia, y por la misma
razón que aquellos: **se añade, no se reemplaza**. Un bucle que reintenta sin memoria
es un bucle que reintenta lo mismo, y la memoria que necesita no es «cuántas veces»:
es **qué medida movió cada vuelta y en qué quedó**. Sin eso no se puede saber si la
vuelta siguiente mejora algo, y la única regla que quedaría contra el reintento
infinito sería un contador que no dice nada del asset.

Lo que se anota, por vuelta:

```text
la medida que la motivo, su valor entonces y su tope      que se estaba mirando
la etapa y sus parametros                                 que se propuso hacer
la distancia contra la malla medida, si se pudo leer      el freno (F2)
```

La distancia se lee de la etapa que **pierde geometría** —el decimado, y los niveles
si los hay—, que es donde el freno tiene sentido: una vuelta de UV no mueve un vértice
y su distancia no dice nada de lo que costó.

`olvidar_intentos` deja el registro vacío, y existe porque seguir después de una parada
es una decisión de quien lee los números: se pide, no se asume.
"""

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any

from videomesh.contracts.serialization import volcar_json
from videomesh.project.store import comprobar_proyecto

__all__ = ["INTENTOS", "Intento", "anotar_intento", "intentos_de", "olvidar_intentos"]

#: El registro del bucle, en el proyecto y no en el paquete: describe el viaje, no el
#: asset que se publicó.
INTENTOS = "bucle.jsonl"


@dataclass(frozen=True)
class Intento:
    """Una vuelta del bucle: qué la motivó, qué se propuso y qué costaba el asset."""

    medida: str
    valor: float | None
    limite: float | None
    etapa: str
    parametros: dict[str, Any] = field(default_factory=dict)
    distancia: float | None = None


def anotar_intento(proyecto: pathlib.Path, intento: Intento) -> None:
    """Añade una línea al registro. Una por vuelta, en el orden en que pasó."""
    ruta = comprobar_proyecto(proyecto)
    fila = {
        "medida": intento.medida,
        "valor": intento.valor,
        "limite": intento.limite,
        "etapa": intento.etapa,
        "parametros": intento.parametros,
        "distancia": intento.distancia,
    }
    with (ruta / INTENTOS).open("a", encoding="utf-8") as fichero:
        fichero.write(volcar_json(fila) + "\n")


def intentos_de(proyecto: pathlib.Path) -> list[Intento]:
    """Todo lo anotado, en el orden en que pasó. Vacío si el bucle no ha empezado."""
    ruta = comprobar_proyecto(proyecto)
    fichero = ruta / INTENTOS
    if not fichero.is_file():
        return []

    anotados: list[Intento] = []
    for linea in fichero.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        fila = json.loads(linea)
        anotados.append(
            Intento(
                medida=str(fila["medida"]),
                valor=None if fila["valor"] is None else float(fila["valor"]),
                limite=None if fila["limite"] is None else float(fila["limite"]),
                etapa=str(fila["etapa"]),
                parametros=dict(fila.get("parametros") or {}),
                distancia=None if fila.get("distancia") is None else float(fila["distancia"]),
            )
        )
    return anotados


def olvidar_intentos(proyecto: pathlib.Path) -> None:
    """Vacía el registro: seguir después de una parada se pide, y esto es pedirlo."""
    ruta = comprobar_proyecto(proyecto)
    fichero = ruta / INTENTOS
    if fichero.is_file():
        fichero.unlink()
