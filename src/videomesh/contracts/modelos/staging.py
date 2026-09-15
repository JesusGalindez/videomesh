"""Modelos de `staging.schema.json` — GENERADO, NO EDITAR A MANO.

Lo escribe `scripts/generar_modelos.py` a partir del esquema publicado por
SoftSight (D15). Para cambiarlo, cambia el esquema y vuelve a generar.

esquema sha256: f80ae9d4d378fa1de4838f7c8988a334d487b5b3bc34a6833cf4fa080485bff1
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class StagingFrame(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    width: int | float
    height: int | float


class StagingScenesItemLayersItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    kind: Literal["text", "model", "image", "shape", "particles"]
    visible: bool
    box: Annotated[list[int | float], Field(min_length=4, max_length=4)] | None = Field(default=None)
    color: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)
    backgroundColor: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)


class StagingScenesItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    startFrame: int | float
    durationFrames: int | float
    sampleFrame: int | float
    layers: list[StagingScenesItemLayersItem]


class Staging(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    stagingVersion: int | float
    title: str | None = Field(default=None)
    frame: StagingFrame
    scenes: list[StagingScenesItem]


__all__ = ['Staging']
