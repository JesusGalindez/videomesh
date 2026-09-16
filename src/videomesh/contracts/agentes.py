"""Los bloques generados de `AGENTS.md`.

Un `AGENTS.md` escrito entero a mano miente tres commits despues: alguien anade
una prueba, no la apunta, y el agente frio que llega el mes siguiente ejecuta una
lista incompleta creyendola completa. Es el mismo error que el esquema evita —el
esquema **es** el validador— y aqui se evita igual: la lista de pruebas sale del
disco, los comandos de `scripts/` y las dependencias de `pyproject.toml`, y una
prueba comprueba que lo commiteado es identico a lo regenerado.

Lo que **no** se genera es lo que un script no puede saber: donde va un cambio,
que se rompe si lo tocas y a que documento ir. Eso se escribe a mano, vive fuera
de los delimitadores y la regeneracion no lo toca.
"""

import pathlib
import re
import tomllib

from videomesh.domain.errores import ErrorDeVideoMesh

__all__ = ["TECHO", "ErrorDeBloque", "agents_md_generado", "reemplazar_bloque"]

RAIZ = pathlib.Path(__file__).resolve().parents[3]
AGENTS = RAIZ / "AGENTS.md"

#: Cuantas lineas puede tener `AGENTS.md`, generado entero. Vive aqui y no en el
#: script ni en la prueba porque es **el mismo numero para los dos**: estaba en los
#: dos —150 alli, 150 alla— y el dia que uno de los dos subio, la verificacion se
#: puso roja por una copia en vez de por el fichero.
#:
#: El bloque de pruebas crece una linea por fichero. El encargo 04 anade uno por
#: bloque —seis— asi que sube una vez y con motivo, no cada vez que molesta.
TECHO = 160


class ErrorDeBloque(ErrorDeVideoMesh, RuntimeError):
    """`AGENTS.md` ya no tiene el bloque que el generador reescribe."""


def reemplazar_bloque(texto: str, nombre: str, cuerpo: str) -> str:
    """Sustituye lo de dentro de un bloque y deja intacto todo lo de fuera."""
    abre = f"<!-- generado: {nombre} -->"
    cierra = f"<!-- /generado: {nombre} -->"
    inicio = texto.find(abre)
    fin = texto.find(cierra)
    if inicio < 0 or fin < 0:
        raise ErrorDeBloque(
            f"AGENTS.md no tiene el bloque '{nombre}'; sin el, lo generado no tiene donde ir"
        )
    return f"{texto[: inicio + len(abre)]}\n{cuerpo}\n{texto[fin:]}"


def _proposito(fichero: pathlib.Path) -> str:
    """La primera linea del docstring del modulo de prueba: que cubre."""
    texto = fichero.read_text(encoding="utf-8")
    encontrado = re.match(r'\s*"""(.+)', texto)
    return encontrado.group(1).strip() if encontrado else ""


def _bloque_pruebas() -> str:
    filas = ["| Prueba | Que cubre |", "|---|---|"]
    for fichero in sorted((RAIZ / "tests").glob("test_*.py")):
        filas.append(f"| `{fichero.name}` | {_proposito(fichero)} |")
    return "\n".join(filas)


def _bloque_comandos() -> str:
    ordenes = sorted(
        ruta.name for ruta in (RAIZ / "scripts").iterdir() if ruta.suffix in (".sh", ".py")
    )
    # En una linea y no en tabla: lo que hace cada script ya esta en su docstring,
    # y una tabla de cuatro filas se come el techo sin decir mas.
    generadores = " · ".join(f"`scripts/{nombre}`" for nombre in ordenes if nombre != "verify.sh")
    return (
        "`bash scripts/verify.sh` — **lo primero y lo ultimo**: linter, tipos, pruebas "
        "y que lo publicado este al dia.\n\n"
        f"Vuelven a generar lo que este repositorio publica: {generadores}. "
        "Con `--check` dicen si lo commiteado se ha quedado atras."
    )


def _bloque_dependencias() -> str:
    manifiesto = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    proyecto = manifiesto["project"]
    produccion = " · ".join(f"`{d}`" for d in proyecto["dependencies"])
    desarrollo = " · ".join(f"`{d}`" for d in proyecto["optional-dependencies"]["dev"])
    return (
        f"Python `{proyecto['requires-python']}`, con `uv`.\n\n"
        f"En produccion: {produccion}.\n\n"
        f"Para trabajar: {desarrollo}."
    )


def agents_md_generado() -> str:
    """`AGENTS.md` con sus tres bloques al dia y lo escrito a mano intacto."""
    texto = AGENTS.read_text(encoding="utf-8")
    texto = reemplazar_bloque(texto, "comandos", _bloque_comandos())
    texto = reemplazar_bloque(texto, "pruebas", _bloque_pruebas())
    texto = reemplazar_bloque(texto, "dependencias", _bloque_dependencias())
    return texto
