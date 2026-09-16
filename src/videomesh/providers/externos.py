"""Los binarios de fuera, y qué decir cuando no están — §22 del roadmap.

Un stage que llama a COLMAP sin comprobarlo revienta con un `FileNotFoundError`
de `subprocess` treinta marcos más abajo, y el usuario tiene que deducir de un
*traceback* que le falta un programa. `ProveedorNoDisponible` es de entorno y lo
dice por su nombre.

**El mensaje tiene tres partes y las tres hacen falta**: qué falta, para qué hace
falta, y cómo se instala. Sin la segunda, quien no conozca el pipeline no sabe si
puede seguir sin ello; sin la tercera, tiene que ir a buscarlo fuera.

Aquí no se ejecuta nada todavía: FFmpeg y COLMAP no están en esta máquina, así
que escribir el adaptador entero sería escribirlo contra una documentación en vez
de contra un programa. Lo que sí existe es la frontera donde se comprueban, que
es lo que permite que `analyze` exista y falle bien en vez de no existir.
"""

import shutil
from dataclasses import dataclass

from videomesh.domain.errores import ProveedorNoDisponible

__all__ = ["Externo", "COLMAP", "FFMPEG", "exigir"]


@dataclass(frozen=True)
class Externo:
    """Un programa de fuera: cómo se llama, para qué, y cómo se consigue."""

    orden: str
    para: str
    instalacion: str


FFMPEG = Externo(
    orden="ffmpeg",
    para="extraer los frames del video y leer sus metadatos",
    instalacion="brew install ffmpeg",
)

COLMAP = Externo(
    orden="colmap",
    para="la reconstruccion dispersa y densa a partir de los frames",
    instalacion="brew install colmap",
)


def exigir(externo: Externo) -> str:
    """La ruta del binario, o `ProveedorNoDisponible` diciendo las tres cosas."""
    ruta = shutil.which(externo.orden)
    if ruta is None:
        raise ProveedorNoDisponible(
            f"falta `{externo.orden}`, que hace falta para {externo.para}.\n"
            f"  se instala con: {externo.instalacion}\n"
            "  `videomesh doctor` dice el resto del entorno de una vez"
        )
    return ruta
