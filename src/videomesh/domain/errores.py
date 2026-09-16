"""Los errores del pipeline, tipados — §22 del roadmap.

«No usar excepciones genéricas como estado de pipeline.» Un `ValueError` suelto
obliga a quien lo recibe a leer el mensaje para saber qué pasó, que es el mismo
error que D2 prohíbe en la frontera, un nivel más adentro.

Todo cuelga de `ErrorDeVideoMesh`, asi que quien llama puede capturar lo de este
repositorio sin tragarse un `KeyError` de una librería. Y los que ya existían
**siguen siendo el error de Python que eran** —`ValueError`, casi todos—, porque
cambiar la jerarquía no puede romper a quien ya los capturaba.

Lo que §22 separa y no se debe confundir:

    fallo de software o de proveedor   !=   certificación FAIL o INCONCLUSIVE

«Esto no lo sé hacer», «esto se rompió» y «esto está mal» son tres respuestas
distintas, y quien automatice quiere distinguirlas sin leer el texto.
"""

__all__ = [
    "CapacidadDeComputoAusente",
    "CapacidadNoSoportada",
    "ErrorDeContrato",
    "ErrorDePaquete",
    "ErrorDeProveedor",
    "ErrorDeProyecto",
    "ErrorDeVideoMesh",
    "ManifestNoValido",
    "PaqueteSinSellar",
    "ProcedenciaIncompleta",
    "ProveedorNoDisponible",
    "SinSuperficie",
]


class ErrorDeVideoMesh(Exception):
    """La raíz. Nada de este repositorio lanza algo que no cuelgue de aquí."""


class ErrorDeContrato(ErrorDeVideoMesh):
    """Lo que se escribe o se lee en la frontera con SoftSight no cuadra."""


class ErrorDePaquete(ErrorDeContrato):
    """El paquete de reconstrucción no es publicable o no es interpretable."""


class ErrorDeProyecto(ErrorDeVideoMesh):
    """El proyecto en disco no está, no se puede leer, o no es un proyecto."""


class ErrorDeProveedor(ErrorDeVideoMesh):
    """Algo de fuera —COLMAP, FFmpeg, un binario— falló o no está."""


class ProveedorNoDisponible(ErrorDeProveedor):
    """El proveedor no está instalado o no se puede ejecutar. Es de entorno."""


class CapacidadDeComputoAusente(ErrorDeProveedor):
    """Falta la máquina, no el programa: una GPU, memoria, un sistema operativo."""


class ManifestNoValido(ErrorDePaquete, ValueError):
    """El manifest de un paquete de fuera no valida contra el esquema publicado.

    Es de la frontera y no del formato: el paquete se lee con los modelos que D15
    genera del esquema, asi que un campo que SoftSight no conoce no lo rechaza
    aqui una regla propia — lo rechaza el mismo esquema que lo escribio.
    """


class PaqueteSinSellar(ErrorDePaquete, ValueError):
    """El paquete esta `WRITING`: todavia se esta escribiendo y no se consume (D29)."""


class SinSuperficie(ErrorDePaquete, ValueError):
    """El paquete no trae ninguna `TRIANGLE_MESH`, asi que no hay nada que limpiar."""


class ProcedenciaIncompleta(ErrorDePaquete, ValueError):
    """Falta un dato de procedencia, y sin el la medida no se puede interpretar.

    No es un campo opcional que se deja vacio: de que maquina y con que version
    salio una densa decide si dos densas son comparables, y dentro de seis meses
    nadie se acordara de ninguna de las dos cosas.
    """


class CapacidadNoSoportada(ErrorDeVideoMesh):
    """Se pide algo que este binario **no sabe hacer**, y eso no es un fallo.

    Cuelga aparte de `ErrorDeProveedor` a propósito: un proveedor que no está se
    arregla instalándolo, y una capacidad que no existe se arregla escribiéndola o
    no pidiéndola. Confundirlas manda a quien lo lea a buscar en el sitio
    equivocado.
    """
