"""La medida del vecino: distancia de superficie por `diffMeshes` de SoftSight.

El numero que decide si una etapa esta hecha **no se mide aqui**. Se mide en
SoftSight, que ya tiene el trazador de rayos (`boundsTree`), el muestreo por area
y el suelo de ruido, todo probado contra fuerza bruta. Escribir la distancia en
Python daria dos medidas de lo mismo, y dos medidas acaban discrepando; el dia que
lo hagan, nadie sabra cual manda.

**Una dependencia que no es de este encargo, y como se salva.** `diffMeshes` lee
`.obj` y `.glb`; su `loadFlattenedMesh` no tiene la rama de PLY —`parsePly` ya
existe y falta enchufarlo, y eso esta asignado fuera de aqui—. Para no dejar el
numero en `NOT_RUN` por un formato, las dos mallas se convierten a OBJ con el
proveedor de malla, y **las dos pasan por la misma conversion**: la ida y la
vuelta son simetricas, asi que la distancia sigue siendo la de `diffMeshes` entre
las dos superficies. La conversion va declarada en el informe, y el dia que SoftSight
lea PLY se quita de aqui sin que cambie nada mas.

Cuando no se puede medir —no hay `node`, no esta la herramienta— se levanta
`MedicionNoDisponible`, que es de entorno: quien la reciba publica `NOT_RUN` con su
motivo. Una etapa que se calla no es una etapa que salio bien.
"""

import json
import pathlib
import shutil
import subprocess
from typing import Any

from videomesh.adapters import pymeshlab
from videomesh.contracts.generacion import ESQUEMAS
from videomesh.domain.errores import MedicionNoDisponible

__all__ = ["HERRAMIENTA", "distancia_de_superficie"]

#: La herramienta publica del vecino, que es la unica puerta de medida que hay.
HERRAMIENTA = ESQUEMAS.parent / "tools" / "agent3d.mjs"

#: Muestras por direccion. Se publican en el informe: la cifra sin el muestreo con
#: el que se obtuvo no dice cuanto se miró.
MUESTRAS_POR_DEFECTO = 20_000


def _volcado_de(
    uno: pathlib.Path, otro: pathlib.Path, trabajo: pathlib.Path
) -> tuple[pathlib.Path, pathlib.Path]:
    a = trabajo / "referencia.obj"
    b = trabajo / "salida.obj"
    pymeshlab.a_obj(uno, a)
    pymeshlab.a_obj(otro, b)
    return a, b


def distancia_de_superficie(
    referencia: pathlib.Path,
    salida: pathlib.Path,
    *,
    trabajo: pathlib.Path | None = None,
    herramienta: pathlib.Path | None = None,
    muestras: int = MUESTRAS_POR_DEFECTO,
) -> dict[str, Any]:
    """Las dos direcciones de la distancia entre dos mallas, o `MedicionNoDisponible`.

    La referencia es la malla **medida** y la salida lo que se quiere juzgar. El
    orden importa y por eso se devuelven las dos direcciones separadas: una dice
    cuanta superficie falta y la otra cuanta sobra, que son averias distintas.
    """
    instrumento = pathlib.Path(herramienta) if herramienta is not None else HERRAMIENTA
    if shutil.which("node") is None:
        raise MedicionNoDisponible(
            "no hay `node` para ejecutar diffMeshes: la distancia de superficie la mide "
            "SoftSight y no se reimplementa aqui"
        )
    if not instrumento.is_file():
        raise MedicionNoDisponible(
            f"no esta la herramienta de medida de SoftSight en {instrumento}: la distancia de "
            "superficie la mide su `diffMeshes`, y reimplementarla aqui daria dos medidas de lo "
            "mismo que acabarian discrepando"
        )

    import tempfile

    with tempfile.TemporaryDirectory(prefix="videomesh-diff-", dir=trabajo) as cuna:
        referencia_obj, salida_obj = _volcado_de(referencia, salida, pathlib.Path(cuna))
        orden = [
            "node",
            str(instrumento),
            "--model",
            str(referencia_obj),
            "--diff",
            str(salida_obj),
            "--diff-samples",
            str(muestras),
        ]
        ejecucion = subprocess.run(orden, capture_output=True, text=True, check=False)
    if ejecucion.returncode != 0:
        raise MedicionNoDisponible(
            f"la herramienta de medida fallo ({ejecucion.returncode}): "
            f"{ejecucion.stderr.strip()[-400:] or ejecucion.stdout.strip()[-400:]}"
        )

    informe: dict[str, Any] = json.loads(ejecucion.stdout)
    diff: dict[str, Any] = informe["diff"]
    diagonal = float(diff["boundingBoxDiagonal"])

    def direccion(datos: dict[str, Any]) -> dict[str, Any]:
        maximo = float(datos["maximum"])
        return {
            "maximo": maximo,
            "medio": float(datos["mean"]),
            "rms": float(datos["rms"]),
            # D9: sin referencia de escala no hay milimetros. La fraccion de la
            # diagonal es la unidad del contrato y la unica que no se inventa nada.
            "fraccion_de_la_diagonal": maximo / diagonal if diagonal > 0 else 0.0,
            "desviacion_de_normales_grados": {
                "maximo": float(datos["normalDeviationDegrees"]["maximum"]),
                "medio": float(datos["normalDeviationDegrees"]["mean"]),
            },
        }

    return {
        "estado": "MEDIDA",
        "metodo": "diffMeshes de SoftSight, sobre las dos mallas convertidas a OBJ",
        "comando": " ".join(orden),
        # Las muestras salen de la direccion y no del informe: es el muestreo con
        # el que se obtuvo cada cifra, y se publica para que la cifra se pueda leer.
        "muestras": int(diff["aToB"]["samples"]),
        "semilla": int(diff["seed"]),
        "clase_de_medida": str(diff["measurementClass"]),
        "reproducibilidad": str(diff["reproducibility"]),
        "diagonal": diagonal,
        "suelo_de_ruido": float(diff["noiseFloor"]),
        # La escala la declara el paquete, y esta etapa no la toca (D9).
        "escala": "UNKNOWN",
        # `falta` y `sobra` son las palabras del propio diff: a→b es superficie que
        # falta y b→a superficie que sobra.
        "falta": direccion(diff["aToB"]),
        "sobra": direccion(diff["bToA"]),
        "topologia": diff["topology"],
    }
