#!/usr/bin/env bash
# Verificacion entera del repositorio: linter, tipos y pruebas.
# Es el unico comando que hay que correr; cada tarea del encargo lo pasa completo.
set -euo pipefail

cd "$(dirname "$0")/.."

PY=.venv/bin/python
if [[ ! -x "$PY" ]]; then
  echo "falta .venv — crealo con: uv venv --python ~/.local/bin/python3.12 .venv" >&2
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
