#!/usr/bin/env python
"""Escribe (o comprueba) `contracts/estado.json` del registro de SoftSight — D12.

scripts/generar_estado.py            escribe
scripts/generar_estado.py --check    sale 1 si lo commiteado no esta al dia
"""

import sys

from videomesh.contracts.estado import ESTADO, estado_generado


def main(argumentos: list[str]) -> int:
    contenido = estado_generado()
    actual = ESTADO.read_text(encoding="utf-8") if ESTADO.exists() else None
    if actual == contenido:
        return 0
    if "--check" in argumentos:
        print(
            "contracts/estado.json no esta al dia: alguna version subio en SoftSight.\n"
            "Regeneralo con scripts/generar_estado.py y mira que cambio antes de seguir.",
            file=sys.stderr,
        )
        return 1
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(contenido, encoding="utf-8")
    print(f"escrito {ESTADO.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
