"""VideoMesh — productor de paquetes de reconstruccion.

El consumidor de estos paquetes es SoftSight. La frontera entre los dos la fija
`docs/contrato-videomesh.md`, y de ahi salen las dos constantes de este modulo.
"""

__version__ = "0.0.1"

#: Version del contrato que se escribe en el sobre de todo documento (D16).
CONTRACT_VERSION = "0.1"

__all__ = ["CONTRACT_VERSION", "__version__"]
