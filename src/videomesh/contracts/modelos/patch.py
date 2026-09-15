"""Modelos de `patch.schema.json` — GENERADO, NO EDITAR A MANO.

Lo escribe `scripts/generar_modelos.py` a partir del esquema publicado por
SoftSight (D15). Para cambiarlo, cambia el esquema y vuelve a generar.

esquema sha256: e677c59c5048a4cc7edfdac660708cb8b7a4bc32278a2d9ffca5cc6f8681d444
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class PatchEditsItemObjectRepeatRadial(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    count: int | float
    axis: Literal["x", "y", "z"] | None = Field(default=None)


class PatchEditsItemObjectRepeat(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    radial: PatchEditsItemObjectRepeatRadial | None = Field(default=None)
    mirror: Literal["x", "y", "z"] | None = Field(default=None)
    about: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)


class PatchEditsItemObjectDeformItemTwistDegreesOpcion1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    at: list[list[int | float]]
    ease: str | None = Field(default=None)


class PatchEditsItemObjectDeformItemTwist(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    axis: Literal["x", "y", "z"]
    degrees: int | float | PatchEditsItemObjectDeformItemTwistDegreesOpcion1


class PatchEditsItemObjectDeformItemTaperScaleOpcion1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    at: list[list[int | float]]
    ease: str | None = Field(default=None)


class PatchEditsItemObjectDeformItemTaper(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    axis: Literal["x", "y", "z"]
    scale: int | float | PatchEditsItemObjectDeformItemTaperScaleOpcion1


class PatchEditsItemObjectDeformItemBend(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    axis: Literal["x", "y", "z"]
    into: Literal["x", "y", "z"]
    degrees: int | float


class PatchEditsItemObjectDeformItemWaveAmplitudeOpcion1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    at: list[list[int | float]]
    ease: str | None = Field(default=None)


class PatchEditsItemObjectDeformItemWave(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    axis: Literal["x", "y", "z"]
    along: Literal["x", "y", "z"]
    amplitude: int | float | PatchEditsItemObjectDeformItemWaveAmplitudeOpcion1
    cycles: int | float | None = Field(default=None)
    phase: int | float | None = Field(default=None)


class PatchEditsItemObjectDeformItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    twist: PatchEditsItemObjectDeformItemTwist | None = Field(default=None)
    taper: PatchEditsItemObjectDeformItemTaper | None = Field(default=None)
    bend: PatchEditsItemObjectDeformItemBend | None = Field(default=None)
    wave: PatchEditsItemObjectDeformItemWave | None = Field(default=None)


class PatchEditsItemObjectGeometryOpcion0(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    primitive: Literal["box", "sphere", "torus", "plane", "cylinder", "cone"]
    parameters: list[int | float] | None = Field(default=None)


class PatchEditsItemObjectGeometryOpcion1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    positions: list[int | float]
    indices: list[int | float] | None = Field(default=None)
    normals: list[int | float] | None = Field(default=None)
    uvs: list[int | float] | None = Field(default=None)


class PatchEditsItemObjectGeometryOpcion2(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    extrude: list[int | float] | str
    height: int | float | None = Field(default=None)


class PatchEditsItemObjectGeometryOpcion3(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    revolve: list[int | float]
    segments: int | float | None = Field(default=None)


class PatchEditsItemObjectGeometryOpcion4LoftItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    at: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)
    profile: list[int | float] | str
    scale: int | float | list[int | float] | None = Field(default=None)
    twist: int | float | None = Field(default=None)


class PatchEditsItemObjectGeometryOpcion4Path(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    through: list[list[int | float]]
    kind: Literal["catmull-rom", "polyline"] | None = Field(default=None)
    closed: bool | None = Field(default=None)


class PatchEditsItemObjectGeometryOpcion4(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    loft: list[PatchEditsItemObjectGeometryOpcion4LoftItem]
    samples: int | float | None = Field(default=None)
    caps: Literal["both", "none", "start", "end"] | None = Field(default=None)
    path: PatchEditsItemObjectGeometryOpcion4Path | None = Field(default=None)
    stations: int | float | None = Field(default=None)


class PatchEditsItemObjectGeometryOpcion5Path(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    through: list[list[int | float]]
    kind: Literal["catmull-rom", "polyline"] | None = Field(default=None)
    closed: bool | None = Field(default=None)


class PatchEditsItemObjectGeometryOpcion5RadiusOpcion1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    at: list[list[int | float]]
    ease: str | None = Field(default=None)


class PatchEditsItemObjectGeometryOpcion5TwistOpcion1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    at: list[list[int | float]]
    ease: str | None = Field(default=None)


class PatchEditsItemObjectGeometryOpcion5(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    sweep: list[int | float] | str
    path: PatchEditsItemObjectGeometryOpcion5Path
    radius: int | float | PatchEditsItemObjectGeometryOpcion5RadiusOpcion1 | None = Field(default=None)
    twist: int | float | PatchEditsItemObjectGeometryOpcion5TwistOpcion1 | None = Field(default=None)
    stations: int | float | None = Field(default=None)
    caps: Literal["both", "none", "start", "end"] | None = Field(default=None)


class PatchEditsItemObject(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str | None = Field(default=None)
    repeat: PatchEditsItemObjectRepeat | None = Field(default=None)
    deform: list[PatchEditsItemObjectDeformItem] | None = Field(default=None)
    geometry: PatchEditsItemObjectGeometryOpcion0 | PatchEditsItemObjectGeometryOpcion1 | PatchEditsItemObjectGeometryOpcion2 | PatchEditsItemObjectGeometryOpcion3 | PatchEditsItemObjectGeometryOpcion4 | PatchEditsItemObjectGeometryOpcion5
    matrix: list[int | float] | None = Field(default=None)
    position: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)
    rotation: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)
    scale: int | float | list[int | float] | None = Field(default=None)
    color: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)
    specular: int | float | None = Field(default=None)
    shininess: int | float | None = Field(default=None)


class PatchEditsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    op: Literal["add", "translate", "rotate", "scale", "color", "hide", "show", "delete", "rename", "align", "setPivot", "mirror", "instance"]
    target: str | None = Field(default=None)
    object: PatchEditsItemObject | None = Field(default=None)
    delta: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)
    degrees: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)
    factor: int | float | list[int | float] | None = Field(default=None)
    rgb: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)
    to: str | list[int | float] | None = Field(default=None)
    axis: Literal["x", "y", "z"] | None = Field(default=None)
    gap: int | float | None = Field(default=None)


class Patch(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    edits: list[PatchEditsItem]


__all__ = ['Patch']
