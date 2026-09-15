#!/usr/bin/env python
"""Escribe (o comprueba) los modelos generados de los esquemas de SoftSight — D15.

scripts/generar_modelos.py            escribe
scripts/generar_modelos.py --check    solo dice si lo commiteado esta al dia
"""

import pathlib
import sys

from videomesh.contracts.generacion import generar_modulos

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "src" / "videomesh" / "contracts" / "modelos"


def main(argumentos: list[str]) -> int:
    comprobar = "--check" in argumentos
    modulos = generar_modulos()
    DESTINO.mkdir(parents=True, exist_ok=True)

    desfasados = []
    for fichero, contenido in modulos.items():
        ruta = DESTINO / fichero
        actual = ruta.read_text(encoding="utf-8") if ruta.exists() else None
        if actual == contenido:
            continue
        if comprobar:
            desfasados.append(fichero)
        else:
            ruta.write_text(contenido, encoding="utf-8")
            print(f"escrito {ruta.relative_to(RAIZ)}")

    sobrantes = [r.name for r in DESTINO.glob("*.py") if r.name not in modulos]
    for nombre in sobrantes:
        if comprobar:
            desfasados.append(nombre)
        else:
            (DESTINO / nombre).unlink()
            print(f"borrado {nombre}: su esquema ya no se publica")

    if desfasados:
        print("desfasados respecto al esquema: " + ", ".join(sorted(desfasados)), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
