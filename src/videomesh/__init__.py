"""VideoMesh — productor de paquetes de reconstruccion.

El consumidor de estos paquetes es SoftSight. La frontera entre los dos la fija
`docs/contrato-videomesh.md`.

Aqui **no vive ninguna version del contrato**. D12: el consumidor comprueba el
bloque, no un campo, y una constante suelta seria una segunda fuente del mismo
numero — correcta hoy por casualidad y equivocada en la primera subida. La
combinacion entera se publica en `contracts/estado.json` y se lee con
`videomesh.contracts.estado`.
"""

__version__ = "0.0.1"

__all__ = ["__version__"]
