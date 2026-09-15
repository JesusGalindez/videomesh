"""Modelos de `scene.schema.json` — GENERADO, NO EDITAR A MANO.

Lo escribe `scripts/generar_modelos.py` a partir del esquema publicado por
SoftSight (D15). Para cambiarlo, cambia el esquema y vuelve a generar.

esquema sha256: 1d0c38a2e0cd2e5a0da8c58339f81ad9b525023295515a0cdd86c9ad93da55f6
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SceneObjectsItemRepeatRadial(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    count: int | float
    axis: Literal["x", "y", "z"] | None = Field(default=None)


class SceneObjectsItemRepeat(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    radial: SceneObjectsItemRepeatRadial | None = Field(default=None)
    mirror: Literal["x", "y", "z"] | None = Field(default=None)
    about: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)


class SceneObjectsItemDeformItemTwistDegreesOpcion1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    at: list[list[int | float]]
    ease: str | None = Field(default=None)


class SceneObjectsItemDeformItemTwist(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    axis: Literal["x", "y", "z"]
    degrees: int | float | SceneObjectsItemDeformItemTwistDegreesOpcion1


class SceneObjectsItemDeformItemTaperScaleOpcion1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    at: list[list[int | float]]
    ease: str | None = Field(default=None)


class SceneObjectsItemDeformItemTaper(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    axis: Literal["x", "y", "z"]
    scale: int | float | SceneObjectsItemDeformItemTaperScaleOpcion1


class SceneObjectsItemDeformItemBend(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    axis: Literal["x", "y", "z"]
    into: Literal["x", "y", "z"]
    degrees: int | float


class SceneObjectsItemDeformItemWaveAmplitudeOpcion1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    at: list[list[int | float]]
    ease: str | None = Field(default=None)


class SceneObjectsItemDeformItemWave(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    axis: Literal["x", "y", "z"]
    along: Literal["x", "y", "z"]
    amplitude: int | float | SceneObjectsItemDeformItemWaveAmplitudeOpcion1
    cycles: int | float | None = Field(default=None)
    phase: int | float | None = Field(default=None)


class SceneObjectsItemDeformItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    twist: SceneObjectsItemDeformItemTwist | None = Field(default=None)
    taper: SceneObjectsItemDeformItemTaper | None = Field(default=None)
    bend: SceneObjectsItemDeformItemBend | None = Field(default=None)
    wave: SceneObjectsItemDeformItemWave | None = Field(default=None)


class SceneObjectsItemGeometryOpcion0(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    primitive: Literal["box", "sphere", "torus", "plane", "cylinder", "cone"]
    parameters: list[int | float] | None = Field(default=None)


class SceneObjectsItemGeometryOpcion1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    positions: list[int | float]
    indices: list[int | float] | None = Field(default=None)
    normals: list[int | float] | None = Field(default=None)
    uvs: list[int | float] | None = Field(default=None)


class SceneObjectsItemGeometryOpcion2(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    extrude: list[int | float] | str
    height: int | float | None = Field(default=None)


class SceneObjectsItemGeometryOpcion3(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    revolve: list[int | float]
    segments: int | float | None = Field(default=None)


class SceneObjectsItemGeometryOpcion4LoftItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    at: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)
    profile: list[int | float] | str
    scale: int | float | list[int | float] | None = Field(default=None)
    twist: int | float | None = Field(default=None)


class SceneObjectsItemGeometryOpcion4Path(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    through: list[list[int | float]]
    kind: Literal["catmull-rom", "polyline"] | None = Field(default=None)
    closed: bool | None = Field(default=None)


class SceneObjectsItemGeometryOpcion4(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    loft: list[SceneObjectsItemGeometryOpcion4LoftItem]
    samples: int | float | None = Field(default=None)
    caps: Literal["both", "none", "start", "end"] | None = Field(default=None)
    path: SceneObjectsItemGeometryOpcion4Path | None = Field(default=None)
    stations: int | float | None = Field(default=None)


class SceneObjectsItemGeometryOpcion5Path(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    through: list[list[int | float]]
    kind: Literal["catmull-rom", "polyline"] | None = Field(default=None)
    closed: bool | None = Field(default=None)


class SceneObjectsItemGeometryOpcion5RadiusOpcion1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    at: list[list[int | float]]
    ease: str | None = Field(default=None)


class SceneObjectsItemGeometryOpcion5TwistOpcion1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    at: list[list[int | float]]
    ease: str | None = Field(default=None)


class SceneObjectsItemGeometryOpcion5(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    sweep: list[int | float] | str
    path: SceneObjectsItemGeometryOpcion5Path
    radius: int | float | SceneObjectsItemGeometryOpcion5RadiusOpcion1 | None = Field(default=None)
    twist: int | float | SceneObjectsItemGeometryOpcion5TwistOpcion1 | None = Field(default=None)
    stations: int | float | None = Field(default=None)
    caps: Literal["both", "none", "start", "end"] | None = Field(default=None)


class SceneObjectsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str | None = Field(default=None)
    repeat: SceneObjectsItemRepeat | None = Field(default=None)
    deform: list[SceneObjectsItemDeformItem] | None = Field(default=None)
    geometry: SceneObjectsItemGeometryOpcion0 | SceneObjectsItemGeometryOpcion1 | SceneObjectsItemGeometryOpcion2 | SceneObjectsItemGeometryOpcion3 | SceneObjectsItemGeometryOpcion4 | SceneObjectsItemGeometryOpcion5
    matrix: list[int | float] | None = Field(default=None)
    position: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)
    rotation: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)
    scale: int | float | list[int | float] | None = Field(default=None)
    color: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)
    specular: int | float | None = Field(default=None)
    shininess: int | float | None = Field(default=None)


class SceneProfilesItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    circle: int | float | None = Field(default=None)
    superellipse: list[int | float] | None = Field(default=None)
    gielis: list[int | float] | None = Field(default=None)
    naca: str | None = Field(default=None)
    points: int | float | None = Field(default=None)
    chord: int | float | None = Field(default=None)
    radius: int | float | None = Field(default=None)


class SceneBudgetVolumesItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    part: str
    volume: int | float
    tolerance: int | float | None = Field(default=None)


class SceneBudget(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    triangles: int | float | None = Field(default=None)
    parts: int | float | None = Field(default=None)
    boundaryEdges: int | float | None = Field(default=None)
    degenerateTriangles: int | float | None = Field(default=None)
    symmetryError: int | float | None = Field(default=None)
    watertight: bool | None = Field(default=None)
    volumes: list[SceneBudgetVolumesItem] | None = Field(default=None)


class SceneSkeletonJointsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    parent: str | None = Field(default=None)
    offset: Annotated[list[int | float], Field(min_length=3, max_length=3)] | None = Field(default=None)


class SceneSkeleton(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    joints: list[SceneSkeletonJointsItem]


class SceneBindingsItemBlendOpcion0(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    with_: str = Field(alias="with")
    from_: int | float = Field(alias="from")
    to: int | float
    ease: str | None = Field(default=None)


class SceneBindingsItemBlendOpcion1Item(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    with_: str = Field(alias="with")
    from_: int | float = Field(alias="from")
    to: int | float
    ease: str | None = Field(default=None)


class SceneBindingsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    part: str
    joint: str
    blend: SceneBindingsItemBlendOpcion0 | list[SceneBindingsItemBlendOpcion1Item] | None = Field(default=None)


class SceneClipsItemTracksItemKeysItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    frame: int | float
    value: list[int | float]


class SceneClipsItemTracksItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    joint: str
    property: Literal["translation", "rotation", "scale"]
    interpolation: Literal["linear", "step"] | None = Field(default=None)
    keys: list[SceneClipsItemTracksItemKeysItem] | None = Field(default=None)
    value: dict[str, Any] | None = Field(default=None)
    frames: int | float | None = Field(default=None)
    bake: int | float | None = Field(default=None)
    turns: int | float | None = Field(default=None)
    axis: Literal["x", "y", "z"] | None = Field(default=None)
    cycle: int | float | None = Field(default=None)
    offsetFrames: int | float | None = Field(default=None)


class SceneClipsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str | None = Field(default=None)
    fps: int | float | None = Field(default=None)
    tracks: list[SceneClipsItemTracksItem]


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    objects: list[SceneObjectsItem]
    profiles: list[SceneProfilesItem] | None = Field(default=None)
    budget: SceneBudget | None = Field(default=None)
    skeleton: SceneSkeleton | None = Field(default=None)
    bindings: list[SceneBindingsItem] | None = Field(default=None)
    clips: list[SceneClipsItem] | None = Field(default=None)


__all__ = ['Scene']
