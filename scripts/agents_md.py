#!/usr/bin/env python
"""Reescribe (o comprueba) los bloques generados de `AGENTS.md`.

scripts/agents_md.py            reescribe
scripts/agents_md.py --check    sale 1 si el fichero commiteado no esta al dia
"""

import sys

from videomesh.contracts.agentes import AGENTS, TECHO, agents_md_generado


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
