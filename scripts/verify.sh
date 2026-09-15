#!/usr/bin/env bash
# Verificacion entera del repositorio: linter, tipos y pruebas.
# Es el unico comando que hay que correr; cada tarea del encargo lo pasa completo.
set -euo pipefail

cd "$(dirname "$0")/.."

# El vecino no es opcional: doce de los diecinueve ficheros de prueba leen sus
# esquemas, sus fixtures y su consumidor, y `docs/contrato-videomesh.md` es un
# enlace al suyo. Sin el, esto reventaria doce veces sin decir que lo que falta es
# un repositorio.
VECINO=../Dron/softsight
if [[ ! -d "$VECINO/contracts" ]]; then
  echo "falta el repositorio vecino en $VECINO" >&2
  echo "VideoMesh se escribe contra SoftSight: sus esquemas son la frontera y su" >&2
  echo "consumidor es la puerta. Clonalo al lado de este repositorio." >&2
  exit 1
fi

PY=.venv/bin/python
if [[ ! -x "$PY" ]]; then
  # La version sale del pyproject.toml, como en el workflow de CI: escribirla
  # aqui seria el tercer original, y la ruta que habia era la de una maquina.
  PY_VERSION="$(sed -n 's/^python_version *= *"\([^"]*\)"/\1/p' pyproject.toml)"
  echo "falta .venv — crealo con: uv venv --python $PY_VERSION .venv" >&2
  echo "y luego:                  uv pip install --python .venv/bin/python -e '.[dev]'" >&2
  exit 1
fi

echo "== ruff =="
.venv/bin/ruff check .
.venv/bin/ruff format --check .

echo "== mypy =="
.venv/bin/mypy

echo "== pytest =="
"$PY" -m pytest

# Sin esto, AGENTS.md seria otro documento que depende de que alguien se acuerde,
# que es exactamente el fallo que existe para cerrar.
echo "== publicado al dia =="
"$PY" scripts/agents_md.py --check
"$PY" scripts/generar_estado.py --check
"$PY" scripts/generar_modelos.py --check
"$PY" scripts/generar_expected.py --check

echo "== verde =="
