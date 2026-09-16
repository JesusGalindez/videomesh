#!/usr/bin/env python
"""Reescribe (o comprueba) los bloques generados de `AGENTS.md`.

scripts/agents_md.py            reescribe
scripts/agents_md.py --check    sale 1 si el fichero commiteado no esta al dia
"""

import sys

from videomesh.contracts.agentes import AGENTS, agents_md_generado

# El bloque generado crece una linea por fichero de prueba, asi que el techo es un
# recordatorio y no una promesa: el encargo 04 anade un fichero por bloque —seis—
# y el techo sube una vez y con motivo, no cada vez que molesta.
TECHO = 160


def main(argumentos: list[str]) -> int:
    original = AGENTS.read_text(encoding="utf-8")
    generado = agents_md_generado()
    lineas = generado.count("\n") + 1

    if "--check" in argumentos:
        if generado != original:
            print(
                "AGENTS.md no esta al dia: regeneralo con scripts/agents_md.py.\n"
                "Pasa cuando se anade una prueba o una orden y la lista se queda corta.",
                file=sys.stderr,
            )
            return 1
        if lineas > TECHO:
            print(f"AGENTS.md tiene {lineas} lineas y el techo son {TECHO}.", file=sys.stderr)
            return 1
        print(f"agents-md: al dia ({lineas} lineas de {TECHO})")
        return 0

    AGENTS.write_text(generado, encoding="utf-8")
    print(f"agents-md: reescrito ({lineas} lineas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
