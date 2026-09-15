"""Modelos de `reconstruction-report.schema.json` — GENERADO, NO EDITAR A MANO.

Lo escribe `scripts/generar_modelos.py` a partir del esquema publicado por
SoftSight (D15). Para cambiarlo, cambia el esquema y vuelve a generar.

esquema sha256: 62e41bc8a622cf6c5be57a4b0a87cc84bcea997cd35f32dab2f8f6745641b971
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ReconstructionReportLimitsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    value: int | float
    unit: Literal["bytes", "entradas", "líneas"]
    rationale: str


class ReconstructionReportExtensions(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    policy: str
    honoured: list[str]
    ignored: list[str]


class ReconstructionReportCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    policy: str
    supports: list[str]
    required: list[str]
    provided: list[str]
    unknownProvided: list[str]


class ReconstructionReportRun(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    runId: str
    inputPackageId: str | None = Field(default=None)
    inputManifestSha256: str
    status: Literal["COMPLETE", "ERROR", "UNSUPPORTED"]


class ReconstructionReportVersionsContractsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    value: int | float | str


class ReconstructionReportVersions(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    softsight: str
    contracts: list[ReconstructionReportVersionsContractsItem]


class ReconstructionReportEvidenceArtifactsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    type: str
    sha256: str
    bytes: int | float


class ReconstructionReportEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    artifacts: list[ReconstructionReportEvidenceArtifactsItem]
    requiredEvidence: list[str]
    missingEvidence: list[str]


class ReconstructionReportMeasurementsItemAppliesTo(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    artifactId: str
    sha256: str


class ReconstructionReportMeasurementsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    appliesTo: ReconstructionReportMeasurementsItemAppliesTo
    purelyReconstructed: bool
    vertices: int | float
    triangles: int | float
    degenerateTriangles: int | float
    duplicatePositions: int | float
    boundaryEdges: int | float
    nonManifoldEdges: int | float
    watertight: bool
    signedVolume: int | float
    boundingBoxMin: Annotated[list[int | float], Field(min_length=3, max_length=3)]
    boundingBoxMax: Annotated[list[int | float], Field(min_length=3, max_length=3)]
    frame: str
    measurementClass: Literal["EXACT", "APPROXIMATE", "EXTERNAL_MEASUREMENT"]
    reproducibility: Literal["BITWISE_EXACT", "QUANTIZED", "TOLERANCE"]


class ReconstructionReportFrames(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    measuredIn: str
    declared: list[str]
    reachable: list[str]
    transforms: int | float


class ReconstructionReportCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    measurementClass: Literal["EXACT", "APPROXIMATE", "EXTERNAL_MEASUREMENT"]
    reproducibility: Literal["BITWISE_EXACT", "QUANTIZED", "TOLERANCE"]
    seed: int | float
    samples: int | float
    areaWeighted: bool
    observedAreaRatio: int | float
    triangulatedAreaRatio: int | float
    weakAreaRatio: int | float
    unobservedAreaRatio: int | float
    standardError: int | float
    interval: Annotated[list[int | float], Field(min_length=2, max_length=2)]
    bySeenBy: list[int | float]
    maskedCameras: int | float
    provenanceAware: bool
    certificationEligible: bool
    reason: str | None = Field(default=None)


class ReconstructionReportConfidenceByClass(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    SIN_EVIDENCIA: int | float
    SIN_TRIANGULAR: int | float
    PARALAJE_CORTO: int | float
    SOSTENIDA: int | float


class ReconstructionReportConfidenceParallaxDegrees(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    p05: int | float
    median: int | float
    p95: int | float


class ReconstructionReportConfidenceObliquityDegrees(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    median: int | float
    p95: int | float


class ReconstructionReportConfidenceGroundSampling(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    median: int | float
    p95: int | float


class ReconstructionReportConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    measurementClass: Literal["EXACT", "APPROXIMATE", "EXTERNAL_MEASUREMENT"]
    reproducibility: Literal["BITWISE_EXACT", "QUANTIZED", "TOLERANCE"]
    seed: int | float
    samples: int | float
    areaWeighted: bool
    parallaxThresholdDegrees: int | float
    byClass: ReconstructionReportConfidenceByClass
    parallaxDegrees: ReconstructionReportConfidenceParallaxDegrees | None = Field(default=None)
    obliquityDegrees: ReconstructionReportConfidenceObliquityDegrees | None = Field(default=None)
    groundSampling: ReconstructionReportConfidenceGroundSampling | None = Field(default=None)
    provenanceAware: bool
    certificationEligible: bool
    reason: str | None = Field(default=None)


class ReconstructionReportRepairBoundaryByRisk(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    SAFE: int | float
    REVIEW: int | float
    UNSAFE: int | float


class ReconstructionReportRepairBoundaryRepairsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    defect: str
    repair: str
    risk: Literal["SAFE", "REVIEW", "UNSAFE"]
    reason: str
    breaksPurelyReconstructed: bool
    evidence: dict[str, Any]


class ReconstructionReportRepairBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    measurementClass: Literal["EXACT", "APPROXIMATE", "EXTERNAL_MEASUREMENT"]
    reproducibility: Literal["BITWISE_EXACT", "QUANTIZED", "TOLERANCE"]
    evidenceAware: bool
    omittedLoops: int | float
    byRisk: ReconstructionReportRepairBoundaryByRisk
    repairs: list[ReconstructionReportRepairBoundaryRepairsItem]


class ReconstructionReportBudgetsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    max: int | float
    units: Literal["ABSOLUTE", "RELATIVE_TO_DIAGONAL"]
    unit: str | None = Field(default=None)
    observed: int | float | None = Field(default=None)
    measures: str | None = Field(default=None)
    verdict: Literal["PASS", "FAIL", "NO_EVALUADO"]
    reason: str | None = Field(default=None)


class ReconstructionReportCaptureAdviceSuggestionsItemRegion(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    areaRatio: int | float
    samples: int | float
    centroid: Annotated[list[int | float], Field(min_length=3, max_length=3)]
    normal: Annotated[list[int | float], Field(min_length=3, max_length=3)]
    extent: int | float


class ReconstructionReportCaptureAdviceSuggestionsItemCameraIntrinsics(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    fx: int | float
    fy: int | float
    cx: int | float
    cy: int | float


class ReconstructionReportCaptureAdviceSuggestionsItemCameraDistortion(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    k1: int | float | None = Field(default=None)
    k2: int | float | None = Field(default=None)
    p1: int | float | None = Field(default=None)
    p2: int | float | None = Field(default=None)


class ReconstructionReportCaptureAdviceSuggestionsItemCamera(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    width: int | float
    height: int | float
    pixelOrigin: Literal["TOP_LEFT", "BOTTOM_LEFT"]
    pixelCenter: Literal["CENTER", "CORNER"]
    cameraAxes: Literal["X_RIGHT_Y_DOWN_Z_FORWARD", "X_RIGHT_Y_UP_Z_BACKWARD"]
    intrinsics: ReconstructionReportCaptureAdviceSuggestionsItemCameraIntrinsics
    distortion: ReconstructionReportCaptureAdviceSuggestionsItemCameraDistortion | None = Field(default=None)
    worldFromCamera: Annotated[list[int | float], Field(min_length=16, max_length=16)]


class ReconstructionReportCaptureAdviceSuggestionsItemGain(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    observedAreaRatio: int | float
    triangulatedAreaRatio: int | float
    supportedAreaRatio: int | float
    deltaObserved: int | float
    deltaTriangulated: int | float
    deltaSupported: int | float


class ReconstructionReportCaptureAdviceSuggestionsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    reason: Literal["SIN_EVIDENCIA", "SIN_TRIANGULAR", "PARALAJE_CORTO"]
    intrinsicsFrom: str
    distance: int | float
    region: ReconstructionReportCaptureAdviceSuggestionsItemRegion
    camera: ReconstructionReportCaptureAdviceSuggestionsItemCamera
    gain: ReconstructionReportCaptureAdviceSuggestionsItemGain


class ReconstructionReportCaptureAdvice(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    measurementClass: Literal["EXACT", "APPROXIMATE", "EXTERNAL_MEASUREMENT"]
    reproducibility: Literal["BITWISE_EXACT", "QUANTIZED", "TOLERANCE"]
    seed: int | float
    samples: int | float
    areaWeighted: bool
    parallaxThresholdDegrees: int | float
    coversDeficit: int | float
    suggestions: list[ReconstructionReportCaptureAdviceSuggestionsItem]
    reason: str | None = Field(default=None)


class ReconstructionReportScaleUncertainty(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    model: str
    value: int | float


class ReconstructionReportScale(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    status: Literal["UNKNOWN", "RELATIVE", "ABSOLUTE"]
    source: str
    uncertainty: ReconstructionReportScaleUncertainty | None = Field(default=None)
    boundingBoxDiagonal: int | float
    claimsAbsolutePrecision: bool


class ReconstructionReportCameras(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    declared: int | float
    withImage: int | float


class ReconstructionReportWarningsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    code: str
    reason: str
    message: str
    evidence: dict[str, Any] | None = Field(default=None)


class ReconstructionReport(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    documentType: Literal["softsight.reconstruction-report"]
    contractVersion: str
    execution: Literal["COMPLETE", "PARTIAL", "ERROR", "UNSUPPORTED"]
    certification: Literal["PASS", "FAIL", "INCONCLUSIVE"]
    certificationReason: str | None = Field(default=None)
    certificationPolicy: str
    limits: list[ReconstructionReportLimitsItem]
    extensions: ReconstructionReportExtensions
    capabilities: ReconstructionReportCapabilities
    run: ReconstructionReportRun
    versions: ReconstructionReportVersions
    evidence: ReconstructionReportEvidence
    measurements: list[ReconstructionReportMeasurementsItem]
    frames: ReconstructionReportFrames
    coverage: ReconstructionReportCoverage | None = Field(default=None)
    confidence: ReconstructionReportConfidence | None = Field(default=None)
    repairBoundary: ReconstructionReportRepairBoundary | None = Field(default=None)
    budgets: list[ReconstructionReportBudgetsItem]
    captureAdvice: ReconstructionReportCaptureAdvice | None = Field(default=None)
    scale: ReconstructionReportScale
    cameras: ReconstructionReportCameras
    warnings: list[ReconstructionReportWarningsItem]


__all__ = ['ReconstructionReport']
