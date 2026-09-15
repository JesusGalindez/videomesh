"""Modelos de `reconstruction-package.schema.json` — GENERADO, NO EDITAR A MANO.

Lo escribe `scripts/generar_modelos.py` a partir del esquema publicado por
SoftSight (D15). Para cambiarlo, cambia el esquema y vuelve a generar.

esquema sha256: ec74ea6de28096848da8374a27c78954639aaa7b6fb5cee5f49275df26dacccb
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class ReconstructionPackageProducer(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    version: str


class ReconstructionPackageArtifactsItemOpcion0(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    path: str
    bytes: int | float
    sha256: str
    type: Literal["TRIANGLE_MESH"]
    purelyReconstructed: bool


class ReconstructionPackageArtifactsItemOpcion1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    path: str
    bytes: int | float
    sha256: str
    type: Literal["POINT_CLOUD"]


class ReconstructionPackageArtifactsItemOpcion2(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    path: str
    bytes: int | float
    sha256: str
    type: Literal["IMAGE"]


class ReconstructionPackageArtifactsItemOpcion3(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    path: str
    bytes: int | float
    sha256: str
    type: Literal["DEPTH_MAP"]
    cameraId: str
    depthKind: Literal["OPTICAL_AXIS", "RAY_LENGTH"]


class ReconstructionPackageCamerasItemIntrinsics(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    fx: int | float
    fy: int | float
    cx: int | float
    cy: int | float


class ReconstructionPackageCamerasItemDistortion(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    k1: int | float | None = Field(default=None)
    k2: int | float | None = Field(default=None)
    k3: int | float | None = Field(default=None)
    p1: int | float | None = Field(default=None)
    p2: int | float | None = Field(default=None)


class ReconstructionPackageCamerasItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    imageArtifactId: str
    imageArtifactHash: str
    imageSpace: Literal["ORIGINAL", "RECTIFIED"]
    sourceOrientation: int | float | None = Field(default=None)
    width: int | float
    height: int | float
    pixelOrigin: Literal["TOP_LEFT", "BOTTOM_LEFT"]
    pixelCenter: Literal["CENTER", "CORNER"]
    model: Literal["PINHOLE", "OPENCV"]
    cameraAxes: Literal["X_RIGHT_Y_DOWN_Z_FORWARD", "X_RIGHT_Y_UP_Z_BACKWARD"]
    worldFromCamera: Annotated[list[int | float], Field(min_length=16, max_length=16)]
    intrinsics: ReconstructionPackageCamerasItemIntrinsics
    distortion: ReconstructionPackageCamerasItemDistortion | None = Field(default=None)


class ReconstructionPackageScaleUncertainty(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    model: Literal["NONE", "GAUSSIAN", "INTERVAL"]
    value: int | float


class ReconstructionPackageScale(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    status: Literal["UNKNOWN", "RELATIVE", "ABSOLUTE"]
    source: Literal["NONE", "KNOWN_DISTANCE", "MARKER", "CAMERA_PRIOR", "EXTERNAL_MEASUREMENT", "MANUAL"]
    uncertainty: ReconstructionPackageScaleUncertainty | None = Field(default=None)


class ReconstructionPackageFrameGraphTransformsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: Literal["CAMERA", "RECONSTRUCTION", "ASSET_CANONICAL", "PRODUCTION"] = Field(alias="from")
    to: Literal["CAMERA", "RECONSTRUCTION", "ASSET_CANONICAL", "PRODUCTION"]
    matrix: list[int | float]
    reason: str
    producer: str


class ReconstructionPackageFrameGraph(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    transforms: list[ReconstructionPackageFrameGraphTransformsItem]


class ReconstructionPackageBudgetsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    units: Literal["ABSOLUTE", "RELATIVE_TO_DIAGONAL"]
    unit: str | None = Field(default=None)
    max: int | float


class ReconstructionPackageExtensionsValor(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    required: bool
    data: dict[str, Any] | None = Field(default=None)


class ReconstructionPackage(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    documentType: Literal["videomesh.reconstruction-package"]
    contractVersion: str
    contractSchemaSha256: str | None = Field(default=None)
    packageId: str
    state: Literal["WRITING", "SEALED"]
    producer: ReconstructionPackageProducer
    artifacts: list[ReconstructionPackageArtifactsItemOpcion0 | ReconstructionPackageArtifactsItemOpcion1 | ReconstructionPackageArtifactsItemOpcion2 | ReconstructionPackageArtifactsItemOpcion3]
    cameras: list[ReconstructionPackageCamerasItem] | None = Field(default=None)
    scale: ReconstructionPackageScale
    frameGraph: ReconstructionPackageFrameGraph
    requiredEvidence: list[str] | None = Field(default=None)
    budgets: list[ReconstructionPackageBudgetsItem] | None = Field(default=None)
    requires: list[str] | None = Field(default=None)
    provides: list[str] | None = Field(default=None)
    extensions: dict[Annotated[str, StringConstraints(pattern='^[a-z][a-z0-9]*(\\.[a-z0-9-]+){2,}$')], ReconstructionPackageExtensionsValor] | None = Field(default=None)


__all__ = ['ReconstructionPackage']
