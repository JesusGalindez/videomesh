"""Modelos de `story.schema.json` — GENERADO, NO EDITAR A MANO.

Lo escribe `scripts/generar_modelos.py` a partir del esquema publicado por
SoftSight (D15). Para cambiarlo, cambia el esquema y vuelve a generar.

esquema sha256: f90771f3d20e29de293ab76fbc042958110f67e811f97e034163a6de6d9ddde0
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class StoryScenesItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    role: Literal["apertura", "desarrollo", "giro", "cierre"]
    durationFrames: int | float
    data: dict[str, Any]


class Story(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    storyVersion: int | float
    title: str
    fps: int | float
    scenes: list[StoryScenesItem]


__all__ = ['Story']
