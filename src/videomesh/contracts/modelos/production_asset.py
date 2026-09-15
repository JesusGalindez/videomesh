"""Modelos de `production-asset.schema.json` — GENERADO, NO EDITAR A MANO.

Lo escribe `scripts/generar_modelos.py` a partir del esquema publicado por
SoftSight (D15). Para cambiarlo, cambia el esquema y vuelve a generar.

esquema sha256: fd68b0395b0ab5b2b8becf99d4712f684c019a036f758b43d7f35b15de496b6e
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProductionAssetProducer(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    version: str


class ProductionAssetArtifactsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    path: str
    bytes: int | float
    sha256: str
    role: Literal["MASTER", "LOD", "COLLISION", "TEXTURE"]
    format: Literal["PLY", "GLB"] | None = Field(default=None)
    level: int | float | None = Field(default=None)
    usage: Literal["BASE_COLOR", "NORMAL", "METALLIC_ROUGHNESS", "OCCLUSION", "EMISSIVE"] | None = Field(default=None)


class ProductionAssetTargetBudgetsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    role: Literal["MASTER", "LOD", "COLLISION"] | None = Field(default=None)
    units: Literal["ABSOLUTE", "RELATIVE_TO_DIAGONAL"]
    unit: str | None = Field(default=None)
    max: int | float


class ProductionAssetTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    preset: str
    budgets: list[ProductionAssetTargetBudgetsItem]
    collisionTolerance: int | float | None = Field(default=None)
    collisionSlackMax: int | float | None = Field(default=None)
    collisionSlackTolerance: int | float | None = Field(default=None)
    collisionRequireConvex: bool | None = Field(default=None)
    collisionConvexTolerance: int | float | None = Field(default=None)
    collisionVolumeRatioMax: int | float | None = Field(default=None)
    uvRequired: bool | None = Field(default=None)
    uvOverlapMax: int | float | None = Field(default=None)
    uvDensitySpreadMax: int | float | None = Field(default=None)
    textureMaxSize: int | float | None = Field(default=None)
    texturePowerOfTwo: bool | None = Field(default=None)
    texelDensityMin: int | float | None = Field(default=None)
    uvOutsideMax: int | float | None = Field(default=None)
    lodSilhouetteMax: int | float | None = Field(default=None)
    lodNormalMaxDegrees: int | float | None = Field(default=None)
    lodBoundsMax: int | float | None = Field(default=None)
    lodDeviationMax: int | float | None = Field(default=None)


class ProductionAssetMaterialsItemTextures(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    baseColor: str | None = Field(default=None)
    normal: str | None = Field(default=None)
    metallicRoughness: str | None = Field(default=None)
    occlusion: str | None = Field(default=None)
    emissive: str | None = Field(default=None)


class ProductionAssetMaterialsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    appliesTo: list[str]
    textures: ProductionAssetMaterialsItemTextures | None = Field(default=None)
    wrap: Literal["REPEAT", "CLAMP"]
    doubleSided: bool | None = Field(default=None)
    alphaMode: Literal["OPAQUE", "MASK", "BLEND"] | None = Field(default=None)


class ProductionAssetDerivation(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tool: str | None = Field(default=None)
    note: str | None = Field(default=None)


class ProductionAsset(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    documentType: Literal["softsight.production-asset"]
    contractVersion: str
    assetId: str
    state: Literal["DRAFT", "SEALED"]
    producer: ProductionAssetProducer
    artifacts: list[ProductionAssetArtifactsItem]
    target: ProductionAssetTarget
    materials: list[ProductionAssetMaterialsItem] | None = Field(default=None)
    derivation: ProductionAssetDerivation | None = Field(default=None)


__all__ = ['ProductionAsset']
