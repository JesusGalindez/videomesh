"""Que la deriva entre documento y contrato se vea sola.

`docs/OBLIGACIONES-VIDEOMESH.md` declara en su cabecera el sha256 del contrato
contra el que se escribio su tabla, y explica como comprobarlo. Eso estaba desde
el primer dia y no sirvio de nada: el mecanismo existia y **no estaba conectado a
nada que se ejecute**. Un mes despues la tabla tenia nueve filas caducadas.

Las dos funciones reciben lo que comparan como argumento, a proposito: asi el
caso que las rompe se puede escribir sin tocar ningun documento del repositorio.
Una prueba que solo se ha visto verde no ha demostrado que mire nada.
"""

import re

from videomesh.domain.errores import ErrorDeContrato

__all__ = ["ErrorDeDeriva", "comprobar_hash_declarado", "hash_declarado_en"]

#: La linea de la cabecera, tal y como esta escrita: `sha256 \`<64 hex>\``.
#: Se exige el prefijo para que la puerta no se conforme con cualquier sha256 que
#: aparezca en el documento — la tabla podria estar citando el de otro fichero.
_DECLARACION = re.compile(r"^sha256 `([0-9a-f]{64})`", re.MULTILINE)


class ErrorDeDeriva(ErrorDeContrato, AssertionError):
    """Lo que un documento afirma y lo que el repositorio es ya no coinciden."""


def hash_declarado_en(texto: str) -> str:
    """Devuelve el sha256 que la cabecera declara, o falla si no hay ninguno."""
    encontrado = _DECLARACION.search(texto)
    if encontrado is None:
        raise ErrorDeDeriva(
            "la cabecera no declara contra que contrato se escribio esta tabla; "
            "se espera una linea `sha256 `<64 caracteres hexadecimales>``"
        )
    return encontrado.group(1)


def comprobar_hash_declarado(texto: str, hash_real: str) -> None:
    """Compara lo que el documento declara con el contrato que hay de verdad."""
    declarado = hash_declarado_en(texto)
    if declarado == hash_real:
        return
    raise ErrorDeDeriva(
        "el contrato cambio desde que esta tabla se reviso\n"
        f"  declarado  {declarado[:8]}...\n"
        f"  real       {hash_real[:8]}...\n"
        "revisa docs/OBLIGACIONES-VIDEOMESH.md contra el contrato antes de escribir "
        "codigo que dependa de su tabla: el riesgo no es que la tabla este vieja, "
        "es escribir codigo correcto contra un contrato equivocado y no verlo hasta el final"
    )
