#!/usr/bin/env python
"""Fabrica `cube-v1` y lo publica sellado — V3.

    scripts/generar_cube_v1.py [destino]

Por omision escribe en `fixtures/contracts/cube-v1/`, que no se commitea (D18):
lo escribe el generador, y commitearlo seria tener dos originales del mismo cubo.
"""

import pathlib
import shutil
import sys

from videomesh.application.cube_v1 import generar_cube_v1

POR_OMISION = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "contracts" / "cube-v1"


def main(argumentos: list[str]) -> int:
    destino = pathlib.Path(argumentos[0]) if argumentos else POR_OMISION
    if destino.exists():
        # Un paquete sellado no se reescribe (D29). Aqui se borra a proposito y se
        # dice: esto es el generador del fixture, no una publicacion.
        print(f"borrando {destino}, que ya existia")
        shutil.rmtree(destino)
    generar_cube_v1(destino)
    print(f"cube-v1 publicado en {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
