#!/usr/bin/env bash
# Instala los hooks del repositorio en `.git/hooks`.
#
# Se copian en vez de enlazarse: un enlace a un fichero del arbol de trabajo
# cambia de contenido al cambiar de rama, y el hook que se ejecuta dejaria de ser
# el que se reviso. La copia se compara con el original en cada verificacion.
set -euo pipefail

raiz="$(cd "$(dirname "$0")/.." && pwd)"
destino="$raiz/.git/hooks"
mkdir -p "$destino"

for hook in "$raiz"/scripts/hooks/*; do
  nombre="$(basename "$hook")"
  cp "$hook" "$destino/$nombre"
  chmod +x "$destino/$nombre"
  echo "instalado $nombre"
done
