"""Modelos de `sample-reference.schema.json` — GENERADO, NO EDITAR A MANO.

Lo escribe `scripts/generar_modelos.py` a partir del esquema publicado por
SoftSight (D15). Para cambiarlo, cambia el esquema y vuelve a generar.

esquema sha256: 29bc83e9e7766b448dd0d4ea7f2255cb94f3e8bdfda41a9d845edece47958c28
"""

from pydantic import BaseModel, ConfigDict


class SampleReference(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    mesh: str
    primitive: int | float
    triangle: int | float
    barycentric: list[int | float]


__all__ = ['SampleReference']
