#!/usr/bin/env python
"""Escribe (o comprueba) `fixtures/expected/cube-v1.json` — V4, D23.

scripts/generar_expected.py            escribe
scripts/generar_expected.py --check    sale 1 si el cubo cambio y el oraculo no
"""

import sys

from videomesh.application.expected import EXPECTED, expected_generado


def main(argumentos: list[str]) -> int:
    contenido = expected_generado()
    actual = EXPECTED.read_text(encoding="utf-8") if EXPECTED.exists() else None
    if actual == contenido:
        return 0
    if "--check" in argumentos:
        print(
            "fixtures/expected/cube-v1.json no esta al dia: el cubo cambio y el oraculo no.\n"
            "Mira que cambio antes de regenerarlo: un oraculo que se actualiza\n"
            "solo no afirma nada.",
            file=sys.stderr,
        )
        return 1
    EXPECTED.parent.mkdir(parents=True, exist_ok=True)
    EXPECTED.write_text(contenido, encoding="utf-8")
    print(f"escrito {EXPECTED.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
