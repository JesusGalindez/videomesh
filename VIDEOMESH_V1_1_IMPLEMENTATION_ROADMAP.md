# VIDEOMESH_V1_1_IMPLEMENTATION_ROADMAP.md

## Roadmap profesional V1.1 — contrato primero, reconstrucción después

**Estado:** Plan maestro definitivo de implementación para arrancar VideoMesh.  
**Revisión:** V1.1 — incorpora el contrato SoftSight ↔ VideoMesh D1–D34 y P1–P12 cerrado el 2026-08-12.  
**Objetivo V1:** convertir video o secuencias de imágenes de objetos/escenas rígidas en un **asset 3D profesional, medible, reproducible, optimizado y certificado**, o explicar de forma tipada por qué el preset solicitado no puede ejecutarse o certificarse.  
**Arquitectura:** provider-based, local-first, resumable, cacheable, deterministic-where-possible, evidence-aware, contract-first.  
**Principio rector:** **VideoMesh reconstruye y compila; SoftSight mide, verifica y certifica.**  
**Regla de ejecución V1.1:** **ningún pipeline fotogramétrico comienza antes de demostrar la frontera canónica mediante `cube-v1` + R0-B.**

---

# V1.1 — Cambios normativos respecto a V1.0 del roadmap

Esta revisión no cambia la identidad del producto. Cambia **el orden en el que se construye** para que VideoMesh nazca sobre la frontera contractual ya acordada con SoftSight.

La diferencia esencial es:

```text
ROADMAP ANTERIOR

Foundation
↓
FFmpeg / COLMAP / MVS / Mesh
↓
SoftSight contract cerca del paso 40
```

Ahora:

```text
ROADMAP V1.1

Canonical Contract Foundation
↓
cube-v1
↓
SoftSight R0-B PASS
↓
Project/Pipeline Engine
↓
FFmpeg / COLMAP / MVS / Mesh
↓
sealed reconstruction package
↓
SoftSight QA
```

## Decisiones incorporadas obligatoriamente

La implementación debe respetar desde el primer commit contractual:

```text
filesystem handoff
strict JSON
schema hash verification
package sandbox
artifact bytes + SHA-256
packageId
atomic package sealing
immutable SEALED package
ExecutionStatus != CertificationVerdict
requiredEvidence
ScaleStatus / ScaleSource / uncertainty
canonical CameraSet
canonical image orientation
named distortion parameters
depthKind
FrameGraph
canonical transform algebra
versions / models / capabilities
strict unknown-field rejection
MeasurementClass
ReproducibilityMode
mesh artifact purelyReconstructed
cross-project parity fixtures
```

## Estado del contrato al arrancar VideoMesh

```text
D1–D34        ACORDADAS
PROPUESTAS    0
PRINCIPIOS    P1–P12
```

Una decisión se considera implementada únicamente cuando existe una prueba que falla si se viola.

## Regla P12 aplicada al roadmap

```text
Una medida y una prueba que falla tienen más autoridad
que más prosa de arquitectura.
```

No abrir nuevas decisiones contractuales numeradas antes de que `cube-v1` pase de punta a punta, salvo un bloqueo real de `cube-v1`.

---

# 0. North Star

La experiencia final deseada sigue siendo:

```bash
videomesh build turret.mp4 \
  --capture object-orbit \
  --quality high \
  --target web
```

Pero V1.1 distingue claramente:

```text
project workspace
reconstruction package
production package
SoftSight reports
```

Resultado conceptual:

```text
turret/
├── project.json
├── contracts/
│   └── compatibility.json
├── source/
├── cameras/
│   └── cameras.json
├── reconstruction/
│   ├── packages/
│   │   └── recon-0001/
│   │       ├── reconstruction.json      # videomesh.reconstruction-package
│   │       ├── geometry/
│   │       │   ├── sparse.ply
│   │       │   ├── dense.ply
│   │       │   └── mesh_raw.ply
│   │       └── evidence/
│   │           ├── masks/
│   │           ├── depth/
│   │           └── normals/
│   └── candidates/
├── reports/
│   ├── capture_report.json
│   ├── sfm_report.json
│   ├── dense_report.json
│   ├── reconstruction_report.json       # softsight.reconstruction-report
│   └── production_report.json           # softsight.production-report
├── diagnostics/
│   ├── coverage.png
│   ├── confidence.png
│   ├── boundaries.png
│   └── lod_error.png
└── production/
    ├── packages/
    │   └── production-0001/
    │       ├── production.json          # videomesh.production-package
    │       ├── master.glb
    │       ├── lod0.glb
    │       ├── lod1.glb
    │       ├── lod2.glb
    │       ├── collision.glb
    │       └── textures/
    └── archive/
        └── highpoly-master.*
```

Los nombres concretos de carpetas son una decisión del workspace; **la identidad contractual es `packageId`, no el nombre del directorio**.

La salida final debe cumplir:

```text
✓ reproducible where contractually promised
✓ resumable
✓ measurable
✓ provider-based
✓ cacheable
✓ inspectable
✓ evidence-aware
✓ provenance-aware
✓ artifact-bound
✓ contract-versioned
✓ capability-aware
✓ optimized
✓ validated
✓ production-certified
```

La North Star operativa es:

```text
VIDEO / IMAGES
      ↓
CANONICALIZE
      ↓
MEASURE CAPTURE
      ↓
RECONSTRUCT
      ↓
PACKAGE + SEAL
      ↓
VERIFY
      ↓
REFINE
      ↓
COMPILE
      ↓
PACKAGE + SEAL
      ↓
VALIDATE
      ↓
CERTIFY
      ↓
PRODUCTION ASSET
```

---

# 1. Qué es VideoMesh

VideoMesh NO es:

```text
COLMAP wrapper
OpenMVS wrapper
Blender wrapper
GUI para fotogrametría
```

VideoMesh es:

```text
Pipeline Engine
+
Project Model
+
Artifact Graph
+
Smart Frame Intelligence
+
Capture Intelligence
+
Reconstruction Planning
+
Provider Orchestration
+
Reconstruction Tournament
+
SoftSight Integration
+
Quality Intelligence
+
Capture Advisor
+
Production Compiler
+
Cache / Resume
+
Provenance
+
Reporting
```

---

# 2. Alcance V1

## Soportado

```text
video de objeto rígido
secuencia de imágenes
objeto estático
escena rígida
object orbit
turntable con máscaras
scene capture
```

## No soportado en V1

```text
personas deformándose
animales en movimiento
ropa
dynamic NeRF
4D reconstruction
rigging automático
semantic hierarchy
AI hole hallucination
cloud execution
distributed workers
desktop UI compleja
Gaussian Splatting
NeRF
DUSt3R
MASt3R
VGGT
GLUEMAP
```

Estos quedan para V2+.

---

# 3. Arquitectura V1.1

VideoMesh tiene dos capas de ejecución explícitas.

## 3.1 Contract Bootstrap — antes de fotogrametría

```text
Canonical Schemas
       │
       ▼
Artifact Contract
       │
 ┌─────┼───────────────┐
 ▼     ▼               ▼
CameraSet          FrameGraph          Scale
 │                    │                │
 └──────────────┬─────┴────────────────┘
                ▼
        Reconstruction Package
                │
      sandbox + bytes + SHA256
                │
                ▼
              SEALED
                │
                ▼
             cube-v1
                │
                ▼
          expected.json
                │
                ▼
        SoftSight R0-B parity
                │
                ▼
               PASS
```

Solo después se desbloquea el pipeline de producto dependiente del contrato.

## 3.2 Product Pipeline

```text
                   VIDEO / IMAGES
                         │
                         ▼
                   Media Provider
                       FFmpeg
                         │
                         ▼
             Canonical Media / Frames
               orientation baked
                         │
                         ▼
                  Capture Analyzer
                       OpenCV
                         │
                         ▼
                Smart Frame Selector
                    VideoMesh Core
                         │
                         ▼
                   Mask Provider
                 manual / optional SAM2
                         │
                         ▼
                Calibration Priors
                         │
                         ▼
                      COLMAP
       ┌─────────────────┼─────────────────┐
       │                 │                 │
    features          matching            SfM
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
              Reconstruction Normalize
          canonical CameraSet + FrameGraph
                         │
                         ▼
                  Scale Resolution
                         │
                         ▼
                     SfM Gate
                         │
                         ▼
                  Dense MVS Provider
                 COLMAP PatchMatch
                         │
                         ▼
                   Dense Point Cloud
                         │
                         ▼
                  Mesh Candidates
        Poisson / Delaunay / AdvancingFront
                         │
                         ▼
              Reconstruction Package
                         │
                hash + seal + publish
                         │
                         ▼
                    SoftSight QA
                         │
                         ▼
                Select Best Candidate
                         │
                         ▼
                Production Compiler
                  Blender Provider
                         │
                         ▼
                 Texture / LOD / GLB
                         │
                         ▼
              meshoptimizer + KTX2
                         │
                         ▼
                 glTF Validator
                         │
                         ▼
                 Production Package
                         │
                hash + seal + publish
                         │
                         ▼
                  SoftSight Final
                         │
                         ▼
                  PRODUCTION READY
```

## 3.3 Regla de canonicalización

```text
External backend diversity
          ↓
       Adapter
          ↓
Canonical VideoMesh domain
```

Ejemplos:

```text
COLMAP distortion vector
→ named canonical distortion parameters

cameraFromWorld
→ worldFromCamera

EXIF/video rotation
→ pixels physically canonicalized

provider-native depth
→ canonical evidence with depthKind

glTF matrix serialization
↔ converted exactly once in GLTFAdapter
```

**Adapters absorb backend ambiguity; the canonical contract removes it.**

---

# 4. Dependencias principales

## P0 — necesarias para el camino V1

```text
Python 3.11/3.12
FFmpeg
OpenCV
COLMAP 4.x / PyCOLMAP
SoftSight
NumPy
Pydantic
Typer
SQLite
JSON Schema tooling / canonical schema consumer
SHA-256 from Python stdlib
```

P0 significa que el dominio y los contracts pueden representar correctamente incluso un capability ausente.

## P1 — producción y capacidades opcionales

```text
SAM2
Blender headless
meshoptimizer / gltfpack
BasisU / KTX2
Khronos glTF Validator
```

`SAM2Provider` es opcional y **no bloquea** object-orbit con masks none/manual.

## P2 — post-V1 core / providers experimentales

```text
OpenMVS provider
ALIKED / LightGlue providers
VGGT
GLUEMAP
remote workers
Gaussian AppearanceTwin
GaussianSurfaceProvider
```

## Compute caveat P0

El core puede ejecutarse sin CUDA, pero el preset que solicite COLMAP PatchMatch debe declarar:

```text
Dense COLMAP MVS
requires CUDA-capable provider/runtime
```

No existe fallback ficticio. `videomesh doctor` debe detectarlo antes del stage costoso.

---

# 5. Principio de providers

Nada externo debe contaminar el dominio.

```python
MediaProvider
FrameAnalysisProvider
MaskProvider
CalibrationProvider
ScaleProvider

FeatureProvider
MatchingProvider
SfMProvider
MVSProvider
MeshProvider

GeometryQAProvider

RepairProvider
RetopologyProvider
TextureProvider
BakeProvider
LODProvider

OptimizeProvider
ExportProvider
ValidatorProvider

ComputeProvider
```

Implementaciones V1:

```text
MediaProvider
└── FFmpegProvider

FrameAnalysisProvider
└── OpenCVProvider

MaskProvider
├── None
├── Manual
└── SAM2Provider

SfMProvider
├── COLMAPIncrementalProvider
└── COLMAPGlobalProvider

MVSProvider
└── COLMAPPatchMatchProvider

MeshProvider
├── COLMAPPoissonProvider
├── COLMAPDelaunayProvider
└── COLMAPAdvancingFrontProvider

GeometryQAProvider
└── SoftSightProvider

ProductionProvider
└── BlenderProvider

OptimizeProvider
└── MeshoptimizerProvider

TextureCompressionProvider
└── BasisKTX2Provider

ValidatorProvider
├── KhronosGLTFValidator
└── SoftSightProvider
```

---

# 6. Regla de dependencia

```text
domain
   ↓
ports
   ↓
application
   ↓
providers/adapters
```

Nunca:

```text
domain imports colmap
domain imports ffmpeg
domain imports blender
```

---

# 7. Estructura del repositorio V1.1

```text
videomesh/
│
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── docs/
├── scripts/
├── tests/
├── fixtures/
│   ├── contracts/
│   │   ├── cube-v1/
│   │   ├── unknown-field-v1/
│   │   ├── invalid-path-v1/
│   │   ├── hash-mismatch-v1/
│   │   ├── camera-transform-v1/
│   │   └── image-orientation-v1/
│   └── pipeline/
├── benchmarks/
│
└── src/videomesh/
    │
    ├── domain/
    │   ├── project.py
    │   ├── artifact.py
    │   ├── stage.py
    │   ├── metrics.py
    │   ├── measurement.py
    │   ├── provenance.py
    │   ├── camera.py
    │   ├── frames.py
    │   ├── scale.py
    │   ├── contracts.py
    │   └── errors.py
    │
    ├── contracts/
    │   ├── schema.py
    │   ├── registry.py
    │   ├── compatibility.py
    │   └── serialization.py
    │
    ├── ports/
    │   ├── media.py
    │   ├── frame_analysis.py
    │   ├── masks.py
    │   ├── calibration.py
    │   ├── scale.py
    │   ├── sfm.py
    │   ├── mvs.py
    │   ├── meshing.py
    │   ├── geometry_qa.py
    │   ├── production.py
    │   ├── optimize.py
    │   ├── export.py
    │   ├── validate.py
    │   └── compute.py
    │
    ├── application/
    │   ├── ingest.py
    │   ├── analyze.py
    │   ├── select_frames.py
    │   ├── reconstruct.py
    │   ├── normalize_reconstruction.py
    │   ├── resolve_scale.py
    │   ├── dense.py
    │   ├── mesh.py
    │   ├── package_reconstruction.py
    │   ├── qa.py
    │   ├── produce.py
    │   ├── package_production.py
    │   └── validate.py
    │
    ├── providers/
    │   ├── ffmpeg/
    │   ├── opencv/
    │   ├── sam2/
    │   ├── colmap/
    │   ├── softsight/
    │   ├── blender/
    │   ├── meshoptimizer/
    │   ├── ktx2/
    │   └── gltf_validator/
    │
    ├── adapters/
    │   ├── colmap_camera.py
    │   ├── dense_evidence.py
    │   └── gltf_transforms.py
    │
    ├── pipeline/
    │   ├── graph.py
    │   ├── runner.py
    │   ├── scheduler.py
    │   ├── cache.py
    │   ├── state.py
    │   └── resume.py
    │
    ├── project/
    │   ├── manifest.py
    │   ├── store.py
    │   ├── database.py
    │   ├── artifact_store.py
    │   ├── package.py
    │   └── sealing.py
    │
    ├── reports/
    │   ├── capture.py
    │   ├── sfm.py
    │   ├── dense.py
    │   ├── reconstruction.py
    │   └── production.py
    │
    └── cli/
        └── app.py
```

Los nombres exactos pueden variar si el agente encuentra una distribución más limpia, pero las responsabilidades contractuales no pueden desaparecer ni moverse al dominio de providers externos.

---

# 8. Modelo de proyecto

El dominio V1.1 separa lifecycle global, stage truth y readiness derivado.

```python
Project
Stage
Artifact
Metric
Diagnostic
ProviderRun
SoftSightRun
Capture
CameraSet
Camera
CameraImageSpace
FrameGraph
ScaleState
Reconstruction
ReconstructionPackage
ProductionAsset
ProductionPackage
```

## ProjectLifecycle

Mantenerlo deliberadamente pequeño:

```text
CREATED
ACTIVE
COMPLETED
FAILED
ARCHIVED
```

No duplicar toda la máquina de estados de stages en un único enum global lineal.

## Readiness derivado

```text
MEDIA_READY
SPARSE_READY
DENSE_READY
RECONSTRUCTION_READY
PRODUCTION_READY
```

Readiness se deriva de gates y artifacts válidos; no se asigna arbitrariamente.

## SoftSightRun

```text
PENDING
RUNNING
COMPLETE
ERROR
UNSUPPORTED
```

`CONSUMED` no es estado de package. Un package sellado permanece `SEALED` para siempre.

---

# 9. Artifact model V1.1

Cada resultado debe ser rastreable y criptográficamente identificable.

```python
Artifact:
    id
    type
    path
    bytes
    sha256
    producer
    producer_version
    input_artifacts
    parameters_hash
    provenance
    metadata
```

`created_at` puede existir como metadata operacional, pero jamás participa en identidad, cache key o contract hash.

## Artifact identity

Para el contrato público V1:

```text
bytes
+
sha256
```

son campos obligatorios.

Internamente puede existir una abstracción futura `ContentDigest`, pero el package V1 publica SHA-256 explícito.

## Artifact discriminado

`TRIANGLE_MESH` requiere desde el primer schema:

```text
purelyReconstructed: true | false
```

Semántica:

```text
true
= toda la superficie procede de evidencia de reconstrucción;
  ningún proceso posterior introdujo superficie nueva sin soporte reconstructivo

false
= existe al menos una región de superficie creada/reparada/inferida
  sin respaldo reconstructivo suficiente
```

Ejemplos que pueden preservar `true` si no introducen superficie:

```text
normal recomputation
vertex welding
index optimization
deterministic simplification
format conversion
coordinate transform
```

Ejemplos que obligan a `false`:

```text
hole filling
AI completion
manual modeled missing region
synthetic backside creation
surface extrapolation
```

Para `POINT_CLOUD`, `purelyReconstructed` está ausente y el schema debe rechazarlo si aparece.

## Lineage

```text
video.mp4
  ↓
frame_0082.jpg
  ↓
selected_frames.json
  ↓
sparse model
  ↓
dense.ply
  ↓
mesh_raw.ply       purelyReconstructed=true
  ↓
mesh_repaired.ply  purelyReconstructed=false   [si crea superficie]
  ↓
master.glb
  ↓
lod1.glb
```

---

# 10. Provenance desde el primer commit

Estados generales:

```text
CAPTURED
DERIVED
RECONSTRUCTED
REPAIRED
SIMPLIFIED
BAKED
INFERRED
GENERATED
AUTHORED
```

Regla congelada:

```text
RECONSTRUCTED != INFERRED
```

V1 utiliza provenance coarse-grained a nivel de artifact. Para superficie de mesh, D21 añade `purelyReconstructed` como garantía específica de elegibilidad de certificación.

Futuro V2 puede introducir provenance por región/triángulo sin cambiar la semántica de V1.

Nunca elevar:

```text
REPAIRED / INFERRED
```

a:

```text
OBSERVED / RECONSTRUCTED
```

por conveniencia de scoring.

---

# 11. Stage model

Cada stage mantiene su propia verdad de ejecución:

```text
PENDING
RUNNING
COMPLETE
FAILED
SKIPPED
CACHED
```

Debe producir o registrar:

```text
artifacts
metrics
logs
diagnostics
input hashes
output hashes
duration
resource usage
provider + provider version
stage determinism
```

## StageDeterminism

```text
DETERMINISTIC
DETERMINISTIC_WITH_SEED
BEST_EFFORT
NON_DETERMINISTIC_PROVIDER
```

No confundir con:

```text
MeasurementClass
ReproducibilityMode
```

que pertenecen a métricas.

## Package publishing no es stage completion trivial

Un stage que publica package no puede declararse COMPLETE hasta que:

```text
all artifacts closed
↓
bytes + SHA256 computed
↓
manifest written last with state=SEALED
↓
atomic same-filesystem rename succeeds
```

---

# 12. Pipeline stages V1.1

El pipeline productivo queda explícitamente separado del R0 contractual.

## R0 Contract Bootstrap — fuera del DAG fotogramétrico normal

```text
R0-VM00 CONTRACT REGISTRY
R0-VM01 STRICT JSON
R0-VM02 ARTIFACT CONTRACT
R0-VM03 CAMERA CONTRACT
R0-VM04 FRAMEGRAPH CONTRACT
R0-VM05 SCALE CONTRACT
R0-VM06 PACKAGE SECURITY + HASHES
R0-VM07 PACKAGE SEALING
R0-VM08 CUBE-V1
R0-VM09 EXPECTED PARITY
R0-VM10 SOFTSIGHT R0-B
```

R0-B debe pasar antes de cualquier stage que dependa del contrato compartido.

## Product DAG

```text
S00 PROJECT
S01 INGEST
S02 MEDIA INSPECTION
S03 CANONICAL MEDIA / PROXY
S04 FRAME ANALYSIS
S05 SMART SELECTION
S06 MASKS
S07 CALIBRATION PRIORS
S08 FEATURES
S09 MATCHING
S10 SFM
S11 RECONSTRUCTION NORMALIZATION
S12 SFM QA
S13 SCALE RESOLUTION
S14 UNDISTORT
S15 PATCHMATCH
S16 FUSION
S17 DENSE QA
S18 MESH CANDIDATES
S19 RECONSTRUCTION PACKAGE
S20 SOFTSIGHT RECON QA
S21 MESH SELECTION
S22 REPAIR / REFINE
S23 TEXTURE
S24 MASTER
S25 LOD
S26 PBR / BAKE
S27 GLB
S28 OPTIMIZE / KTX2
S29 GLTF VALIDATOR
S30 PRODUCTION PACKAGE
S31 SOFTSIGHT FINAL
S32 FINAL REPORT
S33 READY
```

## Nuevas etapas críticas

### S03 — Canonical Media / Proxy

La orientación del source se aplica físicamente a los píxeles usados downstream. Intrinsics, masks, depth, normals y CameraSet deben referirse al mismo pixel grid.

### S11 — Reconstruction Normalization

Convierte outputs nativos de COLMAP a:

```text
canonical CameraSet
canonical worldFromCamera
named distortion parameters
canonical FrameGraph
```

### S13 — Scale Resolution

Resuelve el estado final:

```text
ScaleStatus
ScaleSource
unit
uncertainty
```

Puede consumir priors anteriores y reconstrucción ya resuelta.

### S19 — Reconstruction Package

Produce `videomesh.reconstruction-package`, valida schema, hashes, sandbox y publica mediante sealing atómico.

### S30 — Production Package

Identifica exactamente los bytes finales que SoftSight va a certificar.

## Regla de gating

```text
NO visibility/certification semantics sobre cámaras
antes de CameraSet + FrameGraph correctos.

NO SoftSight QA sobre directorios mutables.
SoftSight recibe package SEALED.
```

---

# 13. Roadmap por releases V1.1

# V0.0 — Contract + Core Foundation

## Objetivo

Construir la frontera real antes de fotogrametría y demostrar que VideoMesh puede producir un package que SoftSight interpreta exactamente igual.

## R0-VM — contrato ejecutable

Implementar primero:

```text
strict JSON serializer
allow_nan=False
canonical schema consumer
documentType
contractVersion
contractSchemaHash
Artifact discriminated model
CameraSet
CameraImageSpace
FrameGraph
Scale model
packageId
package sandbox
artifact bytes + SHA256
atomic package sealing
capabilities negotiation
MeasurementClass
ReproducibilityMode
```

## `cube-v1`

Fixture pequeño, analítico y determinista:

```text
unit cube
known triangle count
known bounds
known scale
4 cameras
known worldFromCamera
known 3D→pixel projections
```

Crear:

```text
reconstruction.json
geometry/cube.ply
cameras/cameras.json
expected.json
```

`expected.json` es oracle de test, nunca input productivo.

## Paridad R0-B

Deben pasar:

```text
SoftSight ↔ expected.json
VideoMesh ↔ expected.json
SoftSight ↔ VideoMesh
```

Shared boundary facts iniciales:

```text
vertex count
triangle count
bounds
registered camera count
projection of known points
schema hash
```

No duplicar Coverage/Geometry QA de SoftSight.

## Core Foundation después del contrato

```text
project model
artifact store
stage model
provider contracts
errors
logging
project manifest
SQLite metadata
CLI skeleton
config
cache
resume
CI foundation
```

## CLI Foundation

```bash
videomesh --help
videomesh init project
videomesh status project
videomesh doctor
```

## Gate F0-A

```text
✓ strict JSON rejects NaN/Infinity
✓ unknown core fields rejected
✓ artifact schema discrimination works
✓ package sandbox works
✓ hashes verify
✓ package sealing works
✓ cube-v1 matches expected.json
```

## Gate F0-B

```text
✓ SoftSight R0-B PASS
✓ schema hash compatible
✓ no manual camera/transform correction
```

## No avanzar hasta

```text
✓ F0-A PASS
✓ F0-B PASS
✓ stage resume semantics correct
✓ artifact hashes stable
✓ provider abstraction works
✓ no external provider imports domain
```

---

# V0.1 — Video → Sparse Reconstruction

Primer milestone fotogramétrico.

## FFmpeg ingest

Extraer:

```text
codec
duration
fps
resolution
pixel format
rotation/tags
timestamps
frame count
```

## Canonical media

Aplicar orientación antes de exponer frames al resto del sistema.

```text
source
↓
decode
↓
orientation normalization
↓
canonical frame
```

## Frame extraction API

```text
extract frame by timestamp
extract list of timestamps
extract range
```

## Frame analysis v1

```text
sharpness
brightness
contrast
highlight clipping
shadow clipping
```

## Smart frame selection v1

```text
quality filtering
+
temporal minimum spacing
+
image similarity
```

## COLMAP initial profile

```text
SIFT
sequential matcher
incremental mapper
```

`ColmapAdapter` normaliza cámaras inmediatamente después del solve.

## SfM metrics

```text
selected frames
registered frames
registration ratio
sparse points
observations
track length
reprojection error
```

## Definition of Done

```text
MP4
↓
canonical selected frames
↓
COLMAP sparse model
↓
canonical CameraSet + FrameGraph
↓
SfM report
```

End-to-end por CLI.

---

# V0.2 — Smart Capture Intelligence

Añadir:

```text
optical flow
track survival
motion magnitude
image novelty
feature density
estimated parallax
```

## FrameMetrics V2

```text
sharpness
brightness
contrast
highlight_clipping
shadow_clipping
feature_density
motion_magnitude
track_survival
similarity_previous
similarity_selected
geometric_novelty
estimated_parallax
final_score
```

## Gate

Comparar:

```text
uniform sampling
vs
smart sampling
```

Medir:

```text
registered ratio
sparse point count
reprojection error
runtime
selected-frame count
```

Smart sampling debe mejorar o mantener calidad usando menos recursos/frames.

---

# V0.3 — Capture modes + masks + scale providers

## CaptureMode

```text
OBJECT_ORBIT
OBJECT_TURNTABLE
SCENE
```

## Masks

Core:

```text
None
Manual
```

P1 paralelo:

```text
SAM2Provider
```

SAM2 no bloquea el camino object-orbit.

## CalibrationProvider

```text
AUTO
EXIF
PROFILE
KNOWN
```

## Scale model — ya existe desde V0.0

```text
ScaleStatus
UNKNOWN | RELATIVE | ABSOLUTE

ScaleSource
NONE | KNOWN_DISTANCE | MARKER | CAMERA_PRIOR | EXTERNAL_MEASUREMENT | MANUAL
```

V0.3 añade providers capaces de resolverla, no inventa el contrato.

## Gate

```text
turntable reconstructs without background dominating matches
scale UNKNOWN remains a valid explicit state
absolute budgets rejected when scale is not ABSOLUTE
```

---

# V0.4 — Dense MVS

## COLMAP PatchMatch Provider

```text
undistort
PatchMatch
depth maps
normal maps
fusion
dense cloud
```

Provider-native depth/normals NO son automáticamente evidence contractual.

Cuando se requiera evidencia canónica:

```text
provider-native evidence
↓
EvidenceAdapter
↓
canonical depth/normal artifact
```

Cada depth declara:

```text
depthKind
space
unit
pixel grid
invalid semantics
```

## Dense gate

```text
depth map count
fusion point count
bounding box
density
normal availability
```

## Hardware

Si el selected dense provider requiere CUDA y no existe:

```text
ExecutionStatus = UNSUPPORTED
reason = COMPUTE_CAPABILITY_MISSING
```

No fallback ficticio.

## Definition of Done

```text
VIDEO
→
DENSE POINT CLOUD
```

---

# V0.5 — Mesh Reconstruction + sealed SoftSight handoff

Crear candidates:

```text
Poisson
Delaunay
AdvancingFront
```

Todos terminan en `TRIANGLE_MESH` artifacts con `purelyReconstructed` requerido.

Antes de SoftSight:

```text
mesh candidate
↓
reconstruction package
↓
validate schema
↓
hash
↓
SEALED
↓
SoftSight
```

## SoftSight Reconstruction QA

Interpretar:

```text
ExecutionStatus
COMPLETE | PARTIAL | ERROR | UNSUPPORTED

CertificationVerdict
PASS | FAIL | INCONCLUSIVE
```

Metrics pueden incluir cuando la capability esté disponible:

```text
triangles
boundary loops
non-manifold
components
coverage
confidence
```

No asumir que Coverage/Confidence existen en la primera versión de R0 de SoftSight.

## Gate

Un candidate elegible para gate requerido debe cumplir:

```text
execution == COMPLETE
certification == PASS
```

`INCONCLUSIVE` nunca se trata como PASS.

## Definition of Done

```text
VIDEO
→
VERIFIED RAW MESH
```

---

# V0.6 — Reconstruction Tournament

## Objetivo

Comparar candidates bajo políticas explícitas.

V1 core no depende de ALIKED/LightGlue.

Profiles iniciales pueden variar:

```text
SIFT + incremental + Poisson
SIFT + incremental + Delaunay
SIFT + global + Poisson
SIFT + global + AdvancingFront
```

Providers experimentales posteriores pueden añadir ALIKED/LightGlue.

Cada candidate registra:

```text
candidate_id
feature config
matching config
mapper
dense config
mesh method
runtime
quality metrics
metric model versions
capabilities
```

## Comparabilidad

Solo comparar directamente métricas cuando coinciden:

```text
metric semantics
model version
evidence basis
scale basis
```

## Candidate states

```text
Execution ERROR       → invalid QA candidate
Execution UNSUPPORTED → not evaluated under requested contract
Certification FAIL    → fails required gate
Certification INCONCLUSIVE → not eligible as PASS
Certification PASS    → eligible
```

---

# V0.7 — Production Mesh

## Objetivo

Pasar de reconstrucción verificada a asset utilizable sin destruir provenance.

`ProductionProvider` inicial:

```text
BlenderProvider
```

Operaciones:

```text
cleanup
orientation
origin
scale
normal cleanup
basic retopology/simplification
UV operations
```

## Repair classification

```text
NON_SURFACE_CREATING
SURFACE_CREATING
INFERRED
```

Si una operación crea superficie sin evidencia reconstructiva:

```text
purelyReconstructed = false
```

No automatizar materiales sofisticados todavía.

Conservar high-poly original por separado.

---

# V0.8 — Texturing

`TexturingProvider`:

```text
COLMAP mesh texturer
BlenderProvider
```

Assets:

```text
base color
normal
roughness
metallic
AO
emissive optional
```

Provenance por texture:

```text
CAPTURED
BAKED
ESTIMATED
AUTHORED
```

No confundir apariencia capturada con propiedades PBR intrínsecas.

---

# V0.9 — GLB Production + adapter boundary

Crear:

```text
master.glb
```

Validar:

```text
nodes
meshes
materials
textures
scale
bounds
```

## GLTFAdapter

La conversión entre canonical transform y glTF ocurre exactamente una vez aquí.

Fixture obligatorio antes de producción final:

```text
transform-gltf-v1
canonical → glTF → canonical
```

## Optimization

```text
meshoptimizer / gltfpack
BasisU / KTX2
```

## Khronos validator

```text
0 errors
```

---

# V0.10 — LOD + Collision

Generar:

```text
LOD0
LOD1
LOD2
collision
```

SoftSight mide cuando las capabilities correspondientes existan:

```text
surface distance
normal deviation
silhouette change
triangle budget
```

Ningún LOD se acepta solo por reducción de triángulos.

---

# V0.11 — Capture Advisor

Consume únicamente capabilities realmente disponibles.

Possible inputs:

```text
weak regions
unobserved regions
missing view directions
camera distribution
```

Si faltan capabilities requeridas:

```text
PARTIAL / UNSUPPORTED
```

No inventar recomendaciones.

Rescan conserva lineage por scan y frame.

---

# V0.12 — Provider compatibility expansion — no bloquea V1 core

El core ya soporta interfaces alternativas.

OpenMVS puede implementarse como provider opcional si aporta valor medido:

```text
CPU/dense alternative
alternative reconstruction
alternative texturing
```

No es requisito para demostrar provider architecture.

---

# V0.13 — Operational Hardening

Cache/resume básicos ya existen desde Foundation.

Aquí endurecer:

```text
crash recovery
cache audit
stage invalidation audit
resource metrics
structured logs
manifest migrations
provider compatibility matrix
large-project recovery
package sealing recovery
```

---

# V0.14 — Benchmarks

Datasets:

```text
simple_object
mechanical_object
turret
low_texture
reflective_object
poor_capture
good_capture
turntable
scene
```

Synthetic ground truth:

```text
known mesh
↓
render cameras
↓
reconstruct
↓
SoftSight compare to GT
```

Metrics:

```text
surface distance
normal deviation
coverage
registration ratio
runtime
peak RAM
VRAM
disk
```

`cube-v1` NO vive aquí: es Foundation contract fixture.

---

# V0.15 — CI Expansion + Release Hardening

CI básico existe desde V0.0.

Expandir:

```text
cross-platform contract parity
larger sparse benchmark
dense benchmark if CUDA runner exists
mesh benchmark
production GLB validation
package migration tests
nightly resource gates
```

---

# V1.0 — Production Release

VideoMesh V1.0 significa:

```text
VALID CAPTURE
 ↓
canonical media
 ↓
smart frames
 ↓
SfM
 ↓
canonical CameraSet + FrameGraph
 ↓
scale resolution
 ↓
SfM QA
 ↓
dense MVS
 ↓
mesh candidates
 ↓
SEALED reconstruction package
 ↓
SoftSight reconstruction QA
 ↓
best eligible candidate
 ↓
production processing
 ↓
textures / LOD / collision
 ↓
GLB
 ↓
mesh optimization + KTX2
 ↓
glTF validation
 ↓
SEALED production package
 ↓
SoftSight final certification
 ↓
PRODUCTION_READY
```

---

# 14. Pipeline Engine

El pipeline debe ser un DAG.

```text
Stage
├── id
├── dependencies
├── inputs
├── outputs
├── provider
├── requirements
├── cache policy
└── execution policy
```

Ejemplo:

```text
patchmatch
depends_on:
  - undistort

requires:
  cuda: true
```

---

# 15. Scheduler

V1 puede ser local.

Debe saber:

```text
CPU availability
RAM
CUDA availability
VRAM
disk
```

No hace falta distributed execution.

Sí preparar:

```text
ComputeRequirements
```

---

# 16. ComputeProvider

```text
CPU
CUDA
```

Futuro:

```text
REMOTE
```

Stage declaration:

```yaml
requires:
  cpu: true
  cuda: false
  ram_mb: 4096
```

---

# 17. Resource monitoring

Por stage:

```text
duration
CPU %
RAM peak
GPU %
VRAM peak
disk read/write
artifact sizes
```

No para marketing.

Para debugging y optimization.

---

# 18. Config system

Usar presets + overrides.

Ejemplo:

```yaml
capture: object-orbit
quality: high
target: web

frames:
  max_selected: 260

sfm:
  mapper: incremental

mvs:
  quality: high

production:
  lods: true
  collision: true
```

Evitar cientos de flags CLI.

---

# 19. Presets

## Capture

```text
OBJECT_ORBIT
OBJECT_TURNTABLE
SCENE
```

## Quality

```text
FAST
BALANCED
HIGH
EXTREME
```

## Target

```text
MASTER
GAME
WEB
MOBILE
ARCHIVE
```

---

# 20. CLI V1

```bash
videomesh init
```

```bash
videomesh inspect video.mp4
```

```bash
videomesh analyze video.mp4
```

```bash
videomesh build video.mp4
```

```bash
videomesh reconstruct project/
```

```bash
videomesh produce project/
```

```bash
videomesh validate project/
```

```bash
videomesh resume project/
```

```bash
videomesh status project/
```

```bash
videomesh report project/
```

```bash
videomesh doctor
```

---

# 21. `videomesh doctor`

Debe reportar existencia **y compatibilidad**.

Ejemplo:

```text
FFmpeg                         AVAILABLE
OpenCV                         AVAILABLE
COLMAP                         AVAILABLE
CUDA                           AVAILABLE / UNAVAILABLE
SoftSight binary               AVAILABLE
SoftSight reconstruction       COMPATIBLE / INCOMPATIBLE
SoftSight schema hash          MATCH / MISMATCH
SoftSight production           COMPATIBLE / INCOMPATIBLE
Blender                        AVAILABLE / UNAVAILABLE
meshoptimizer                  AVAILABLE / UNAVAILABLE
BasisU                         AVAILABLE / UNAVAILABLE
glTF Validator                 AVAILABLE / UNAVAILABLE
```

Capabilities:

```text
Sparse reconstruction          AVAILABLE
Dense COLMAP MVS               AVAILABLE / UNSUPPORTED_ON_CURRENT_COMPUTE
Production GLB                 AVAILABLE / UNAVAILABLE
KTX2                           AVAILABLE / UNAVAILABLE
camera.pinhole.v1              SUPPORTED / UNSUPPORTED
camera.opencv.v1               SUPPORTED / UNSUPPORTED
```

Regla:

```text
incompatibilidad contractual conocida
→ fail fast antes de etapas costosas
```

---

# 22. Failure model V1.1

Errores tipados del pipeline:

```text
MediaError
FrameSelectionError
CalibrationError
SfMError
DenseError
MeshingError
QAError
ProductionError
ValidationError
ProviderUnavailable
ComputeCapabilityMissing
ContractMismatch
PackageInvalid
PackagePathEscape
PackageHashMismatch
PackageNotSealed
PackageAtomicPublishUnavailable
SchemaValidationError
SchemaHashMismatch
CapabilityUnsupported
CameraConventionError
ScaleContractError
```

No usar excepciones genéricas como estado de pipeline.

Tampoco confundir:

```text
software/provider failure
```

con:

```text
certification FAIL / INCONCLUSIVE
```

---

# 23. Retry policy

Retry solo cuando tiene sentido.

```text
temporary provider crash
→ retry

bad capture
→ do not retry

CUDA missing
→ do not retry

invalid manifest
→ do not retry
```

---

# 24. SfM Gate

No ejecutar dense si sparse es mala.

Ejemplos iniciales configurables:

```text
min registration ratio
max reprojection error
min sparse points
min track length
```

No hardcodear como verdad universal.

---

# 25. Dense Gate

No meshing si dense es claramente inválida.

Medir:

```text
fused points
bounds
density
normal coverage
```

---

# 26. SoftSight Reconstruction Gate

VideoMesh no envía blobs por bridge. Envía la ruta de un:

```text
videomesh.reconstruction-package
state = SEALED
```

SoftSight devuelve un:

```text
softsight.reconstruction-report
```

con dos ejes:

```text
ExecutionStatus
COMPLETE | PARTIAL | ERROR | UNSUPPORTED

CertificationVerdict
PASS | FAIL | INCONCLUSIVE
```

Además:

```text
appliesTo.artifactId
appliesTo.sha256
versions
models
capabilities
metrics
warnings
diagnostics refs
```

## Gate requerido

Cuando el target exige certification:

```text
execution == COMPLETE
+
certification == PASS
```

`INCONCLUSIVE` nunca equivale a PASS.

## requiredEvidence

```text
missing required evidence
→ COMPLETE + INCONCLUSIVE
```

si el package es válido y el análisis no puede sostener la decisión.

## D21

Si una métrica de observation coverage intenta certificar un `TRIANGLE_MESH`:

```text
purelyReconstructed == true
```

es requisito para elegibilidad del modelo V1 provenance-unaware.

---

# 27. Production Gate

Debe comprobar:

```text
triangle budget
LOD fidelity
UV
tangents
textures
collision
scale
bounds
GLB production contract
artifact hashes
FrameGraph consistency
```

El objeto exacto a certificar debe estar dentro de un `videomesh.production-package` sellado.

SoftSight no certifica un workspace mutable.

---

# 28. Final readiness

Nunca:

```text
file exists
=
ready
```

Debe ser:

```text
glTF Validator
0 errors
        +
SoftSight execution
COMPLETE
        +
SoftSight certification
PASS
        +
production artifact hash
matches sealed package
        =
PRODUCTION_READY
```

Si SoftSight devuelve:

```text
INCONCLUSIVE
```

un contrato que exige esa certificación queda:

```text
NOT PRODUCTION_READY
```

sin confundirlo con un runtime ERROR.

---

# 29. Project manifest

`project.json` es metadata del workspace; **no es el reconstruction package**.

Debe registrar:

```text
project version
source
capture mode
selected preset
provider choices
stages
artifacts
packageIds
provenance
quality summaries
hardware
contract compatibility snapshot
```

No usar `project.json` como sustituto del manifest sellado que cruza la frontera con SoftSight.

---

# 30. Reproducibility manifest

Registrar por run/stage:

```text
VideoMesh version
Python version
FFmpeg version
OpenCV version
COLMAP version
SoftSight version
Blender version
meshoptimizer version
BasisU version
glTF Validator version
provider parameters
random seeds
hardware
CUDA version
GPU model
stage determinism
contract schema hashes
metric model versions
```

Separar metadata operacional de identidad de artifact.

No introducir timestamps/paths temporales en hashes deterministas.

---

# 31. Determinism policy V1.1

Existen tres niveles distintos.

## 31.1 StageDeterminism

```text
DETERMINISTIC
DETERMINISTIC_WITH_SEED
BEST_EFFORT
NON_DETERMINISTIC_PROVIDER
```

Describe el stage/provider.

## 31.2 MeasurementClass

```text
EXACT
DETERMINISTIC_APPROXIMATION
HEURISTIC
EXTERNAL_MEASUREMENT
```

Describe qué clase de afirmación hace la métrica.

## 31.3 ReproducibilityMode

```text
BITWISE_EXACT
QUANTIZED
TOLERANCE
```

Describe estabilidad numérica.

Regla D28:

```text
BITWISE_EXACT por defecto.
TOLERANCE solo después de medir una divergencia real y registrarla.
```

## Reducciones paralelas

Si una métrica compartida depende de sumas/reducciones:

```text
fixed block size
block boundaries by input indices
worker count does not change partition
final reduction in block-index order
```

El tamaño de bloque pertenece a la especificación/version del modelo de métrica si afecta el resultado.

---

# 32. Smart frame selector roadmap interno

## V1 selector

```text
blur
exposure
time spacing
similarity
```

## V2 selector

```text
optical flow
feature density
track survival
estimated parallax
```

## V3 selector

```text
coverage-aware online selection
```

No meter V3 en V0.1.

---

# 33. Mask roadmap

## V0.1

```text
none/manual
```

## V0.3

```text
SAM2
```

## V2

```text
semantic object-aware masks
```

---

# 34. Reconstruction tournament scoring

No usar un único score como sustituto de gates.

Guardar componentes:

```text
registration
reprojection
coverage
confidence
topology
fragmentation
runtime
resource use
```

Cada componente declara, cuando aplique:

```text
model version
MeasurementClass
ReproducibilityMode
scale/evidence basis
```

VideoMesh puede mantener:

```text
candidateScoreVersion
```

pero el score sirve para:

```text
ranking
UI summary
tie-breaking among eligible candidates
```

Nunca convierte:

```text
FAIL / INCONCLUSIVE
```

en PASS.

---

# 35. Production compiler

Debe ser un orchestrator.

No implementar internamente:

```text
retopology engine
UV engine
baker
```

Los providers lo hacen.

VideoMesh decide:

```text
input artifact
target
budget
sequence
validation
provenance transition
```

## Provenance-aware production

Cada operación debe declarar si:

```text
preserves reconstructed surface
creates repaired surface
creates inferred/authored surface
```

Eso actualiza `purelyReconstructed` del mesh output y su provenance. No se deduce después mirando la geometría.

---

# 36. SoftSight integration contract — V1.1

La autoridad de la frontera vive en el contrato canónico SoftSight ↔ VideoMesh, no en esta sección. Este roadmap implementa sus decisiones.

## Transport

```text
filesystem + paths
```

No base64 package. No streaming V1.

## VideoMesh → SoftSight

Un único entry point:

```text
/path/to/reconstruction.json
```

Documento:

```text
documentType = videomesh.reconstruction-package
contractVersion = 0.x DRAFT / 1.x STABLE
packageId
state = SEALED
contractSchemaHash
artifacts[]
CameraSet
FrameGraph
Scale
versions
models/capability requirements
requiredEvidence
```

Artifact mínimo:

```text
id
kind/type
path
bytes
sha256
```

`TRIANGLE_MESH` añade required:

```text
purelyReconstructed
```

## Package security

Todo artifact interno:

```text
canonical path ∈ PACKAGE_ROOT
```

Rechazar:

```text
../
absolute outside root
symlink escape
broken symlink
```

## Package sealing

```text
write artifacts
↓
close
↓
hash
↓
write manifest last with state=SEALED
↓
atomic same-filesystem rename
```

Final destination sellado no se reescribe.

## SoftSight → VideoMesh

Autoridad primaria:

```text
documentType = softsight.reconstruction-report
```

Contiene:

```text
execution
certification
inputs/appliesTo
versions
models
capabilities
metrics
warnings
diagnostic refs
```

Coverage/confidence/geometry diff pueden tener artifacts auxiliares, pero no son contratos raíz competidores salvo que el contrato canónico lo defina explícitamente.

## Compatibility

VideoMesh verifica:

```text
contractVersion
contractSchemaHash
required capabilities
```

antes de ejecutar QA costoso.

---

# 37. Production contract V1.1

VideoMesh produce un:

```text
videomesh.production-package
```

sellado e inmutable.

Puede contener:

```text
production.json
master.glb
lod*.glb
collision.glb
textures/
```

Cada artifact declara:

```text
id
path
bytes
sha256
provenance
frame/transform applicability where needed
```

SoftSight devuelve:

```text
softsight.production-report
```

con:

```text
ExecutionStatus
CertificationVerdict
appliesTo
metrics
warnings
diagnostics
versions/models/capabilities
```

No usar `PASS/FAIL` sin el eje de ejecución.

---

# 38. Licensing architecture

Mantener herramientas externas separadas.

No enlazar todo en un binario monolítico.

Crear:

```text
ProviderLicenseInfo
```

Registrar:

```text
tool
version
license
distribution mode
```

Especial cuidado con:

```text
OpenMVS
Blender
FFmpeg build
future AI models
```

---

# 39. Seguridad de datos

Por defecto:

```text
local-first
```

No subir videos.

No network dependency para core pipeline.

Future cloud provider debe ser opt-in.

---

# 40. Logging

Structured logs.

```json
{
  "stage": "sfm",
  "provider": "colmap",
  "event": "registered_images",
  "value": 211
}
```

También:

```text
human readable console
```

---

# 41. Reports

## VideoMesh-owned reports

```text
capture_report.json
sfm_report.json
dense_report.json
final_report.json
```

## SoftSight-owned reports

```text
softsight.reconstruction-report
softsight.production-report
```

No duplicar la lógica de SoftSight en reports VideoMesh.

## Binding

Todo report de QA externo debe poder responder:

```text
what exact artifact?
what sha256?
what packageId?
what contract/schema?
what model version?
what capabilities?
```

---

# 42. Quality score ownership

VideoMesh puede producir summaries/rankings sobre sus propias decisiones:

```text
Capture Score
SfM Score
Dense Score
Candidate Ranking Score
```

SoftSight produce métricas y veredictos de su dominio:

```text
Geometry metrics
Coverage metrics
Confidence metrics
Production metrics
CertificationVerdict
```

VideoMesh puede mostrar un `Final Asset Summary Score` solo como UI/ranking, nunca como fuente de certificación.

# 43. No opaque scores

Siempre reportar componentes y gates.

Ejemplo:

```text
Summary Score       94   [informativo]

Capture             91
SfM                 96
Dense               93
Geometry             —   SoftSight metrics below
Coverage            92
Production          95

Required gates:
SoftSight Recon     PASS
Khronos Validator  PASS
SoftSight Production PASS
```

`PRODUCTION_READY` depende de gates explícitos, no del score compuesto.

---

# 44. Benchmark strategy

Nunca decir:

```text
VideoMesh is better
```

sin benchmark.

Comparar:

```text
uniform frames
vs
smart frames

incremental
vs
global

SIFT
vs
ALIKED+LightGlue

Poisson
vs
Delaunay
vs
AdvancingFront
```

---

# 45. Synthetic benchmark

Ideal para exactitud.

```text
known mesh
↓
Blender render
↓
video/images
↓
VideoMesh
↓
reconstruction
↓
SoftSight compare to GT
```

Metrics:

```text
Chamfer-like symmetric distance
surface coverage
normal deviation
bounds error
volume error
```

---

# 46. Real benchmark

Datasets:

```text
turret
shoe
statue
mechanical component
household object
room
```

No usar solo objetos fáciles.

---

# 47. Performance benchmark

Registrar:

```text
time
CPU
RAM
GPU
VRAM
disk
output sizes
```

Por stage.

---

# 48. Hardware profiles

No prometer que todos corren igual.

Profiles:

```text
CPU_ONLY
CUDA_LOW
CUDA_MID
CUDA_HIGH
```

VideoMesh doctor detecta.

---

# 49. macOS

Diseñar core multiplataforma.

En Mac sin CUDA, como mínimo:

```text
contract foundation
project orchestration
FFmpeg ingest
frame intelligence
COLMAP sparse where supported
CameraSet normalization
SoftSight QA
production CPU operations where available
```

Dense COLMAP PatchMatch debe declarar requirements reales.

`videomesh doctor` debe mostrar:

```text
Dense COLMAP MVS
UNSUPPORTED_ON_CURRENT_COMPUTE
```

si no hay provider capaz.

No fingir fallback.

---

# 50. Linux

Debe ser el primary high-performance target para CUDA.

---

# 51. Windows

Support after core stability.

No bloquear V0.x por UI/installer Windows.

---

# 52. Release policy

Cada release debe tener:

```text
migration notes
contract versions
schema hashes
provider compatibility
capability compatibility
benchmark deltas
known limitations
```

Ninguna release puede cambiar semántica de contract version existente sin:

```text
version bump
or
new capability
```

---

# 53. Contract versions V1.1

Separar:

```text
internal VideoMesh model versions
```

de:

```text
public cross-project document contracts
```

## Documento público

Cada documento canónico declara:

```text
documentType
contractVersion
contractSchemaHash
```

Namespaces:

```text
videomesh.reconstruction-package
videomesh.production-package
softsight.reconstruction-report
softsight.production-report
```

## Bloque de versiones

Conceptualmente:

```text
versions:
  package
  camera
  observations
  production

models:
  coverage
  confidence
  geometryDiff
```

## Capabilities

```text
requires
provides
supports
```

Unknown required capability:

```text
UNSUPPORTED
```

## Internal versions

VideoMesh puede mantener:

```text
projectModelVersion
artifactModelVersion
candidateScoreVersion
frameSelectorVersion
```

sin confundirlos con el public contract.

---

# 54. Database

SQLite para:

```text
stages
artifacts
metrics
runs
providers
diagnostics
```

No PostgreSQL para V1.

Proyecto debe seguir siendo portable.

---

# 55. Artifact files

No meter blobs gigantes en SQLite.

SQLite guarda metadata.

Files en project directory.

---

# 56. Cache

Ejemplo:

```text
.cache/
├── media/
├── frames/
├── colmap/
├── dense/
├── mesh/
├── softsight/
└── production/
```

---

# 57. Resume contract

Un stage COMPLETE con artifact hash válido:

```text
skip
```

Si artifact falta:

```text
invalidate
```

Si config cambió:

```text
invalidate dependent stages
```

---

# 58. Stage dependency graph

El DAG V1.1 debe reflejar packages explícitos.

```text
video
↓
canonical frames
↓
features / matches
↓
sfm
↓
reconstruction normalization
↓
scale resolution
↓
dense
↓
mesh candidates
↓
sealed reconstruction package
↓
SoftSight reconstruction QA
↓
selected mesh
↓
production
↓
glTF validation
↓
sealed production package
↓
SoftSight final
↓
ready
```

Cambiar:

```text
LOD target
```

no invalida:

```text
SfM
dense
raw mesh
reconstruction package
```

pero sí invalida los artifacts derivados de producción y su certification report.

Cambiar CameraSet/FrameGraph invalida cualquier métrica/reconstruction artifact que dependa de esas convenciones.

---

# 59. CLI output philosophy

Claro y compacto.

Ejemplo:

```text
S05 Smart Selection
1200 → 214 frames
17.8%

S10 SfM
211 / 214 registered
98.6%

S15 Dense
4.8M points

S17 SoftSight
coverage 96.7%
confidence 94.1%

S28 Final
PRODUCTION_READY
```

---

# 60. Diagnostics

Cuando falla, debe decir:

```text
what
where
evidence
next action
```

Ejemplo:

```text
FAIL: LOW_VIEW_DIVERSITY

Evidence:
selected cameras span only 41° azimuth

Recommended:
capture another orbit
```

---

# 61. Capture Advisor V1

No necesita AI generativa.

Usa únicamente evidence/capabilities disponibles:

```text
coverage
camera distribution
surface normals
weak regions
missing view directions
```

Puede producir:

```text
recommended view cone
recommended azimuth/elevation range
additional frame count
```

Si la capability necesaria no está disponible:

```text
PARTIAL
or
UNSUPPORTED
```

No inventar una recomendación para aparentar completitud.

---

# 62. Object-orbit protocol

V1 documentation:

```text
object static
camera moves slowly
constant focus
constant exposure when possible
diffuse light
high overlap
avoid reflections
multiple elevations
```

---

# 63. Turntable protocol

```text
camera fixed
object rotates
background masked
turntable masked
fixed lighting
fixed focal settings
```

---

# 64. Scene protocol

```text
slow camera
consistent exposure
overlap
avoid moving people
avoid motion blur
```

---

# 65. V2+ backlog

Después de estabilizar V1:

```text
VGGTProvider
GLUEMAPProvider
ALIKED / LightGlue providers
OpenMVS expansion
multi-video
distributed workers
remote CUDA
semantic segmentation
mechanical decomposition
material inference
AI-assisted repair
NeRF
dynamic reconstruction
desktop UI
mobile capture assistant
```

Gaussian se divide explícitamente:

```text
AppearanceTwin
└── GaussianProvider

SurfaceReconstructionProvider
└── GaussianSurfaceProvider
```

El primero modela apariencia; el segundo solo puede entrar al Geometry Tournament si produce superficie explícita auditable por SoftSight.

---

# 66. Lo que NO debemos construir

No crear desde cero:

```text
codec stack
feature detector
feature matcher
bundle adjustment
PatchMatch
Poisson mesher
glTF validator
Blender-like DCC
GPU texture compressor
```

Nuestro valor no está ahí.

---

# 67. Priority map V1.1

## P0 — bloqueante para la arquitectura correcta

```text
strict JSON serialization
canonical schema consumer
Artifact contract
CameraSet
CameraImageSpace
canonical image orientation
FrameGraph
Scale contract
packageId/documentType
package sandbox
artifact bytes + SHA256
atomic package sealing
capability negotiation
MeasurementClass/ReproducibilityMode
cube-v1 + expected.json
SoftSight R0-B
project system
pipeline engine
provider contracts
cache/resume basic
CI foundation
FFmpeg
frame intelligence
COLMAP sparse
COLMAP dense provider contract
mesh candidates
sealed SoftSight integration
reports
CLI
```

## P1 — producción / optional value

```text
Manual masks
SAM2 provider
scale providers (marker/known distance)
calibration profiles
Blender production
GLB
GLTFAdapter
meshoptimizer
KTX2
glTF validator
LOD
collision
Capture Advisor
```

## P2 — después del core V1

```text
OpenMVS provider
ALIKED/LightGlue
AI providers
remote compute
desktop UI
Gaussian providers
```

Importante:

```text
Scale MODEL = P0
Scale advanced PROVIDERS = P1
```

---

# 68. Exact implementation sequence V1.1

Éste es el orden normativo para el agente CLI.

## Phase R0-VM — Contract Bootstrap

```text
01. repository skeleton + CI foundation
02. strict JSON serializer (`allow_nan=False`)
03. canonical schema consumer / generator compatibility layer
04. documentType + contractVersion + schema-hash primitives
05. Artifact domain model
06. discriminated artifact schemas
07. TRIANGLE_MESH.purelyReconstructed required
08. CameraSet + Camera models
09. CameraImageSpace + canonical orientation rules
10. named distortion parameter models
11. FrameGraph domain model
12. canonical transform algebra
13. ScaleStatus / ScaleSource / uncertainty
14. capability negotiation (`requires/provides/supports`)
15. MeasurementClass
16. ReproducibilityMode
17. packageId + package manifest domain
18. package sandbox/path canonicalization
19. artifact bytes + SHA256 verification
20. atomic same-filesystem package sealing
21. cube-v1 generator
22. expected.json golden values
23. VideoMesh parity harness
24. SoftSight compatibility handshake
25. R0-B cross-project test
```

**STOP:** no comenzar FFmpeg/COLMAP si R0-B falla en schema, artifact identity, camera projection, transform convention o package integrity.

## Phase F0 — Core Foundation

```text
26. Project model
27. SQLite metadata
28. Stage state machine
29. Pipeline DAG
30. cache
31. resume
32. structured logging
33. CLI skeleton
34. doctor command with contract/capability checks
```

## Phase M1 — Media + Sparse

```text
35. FFmpeg provider
36. media inspection
37. canonical orientation normalization
38. frame extraction
39. frame metrics v1
40. smart selector v1
41. COLMAP provider shell/PyCOLMAP abstraction
42. feature extraction
43. sequential matching
44. incremental SfM
45. ColmapAdapter → canonical CameraSet
46. FrameGraph population
47. SfM report
48. SfM gate
```

## Phase M1.5 — Capture intelligence

```text
49. frame selector benchmark
50. optical flow metrics
51. smart selector v2
52. mask contract none/manual
53. calibration provider contracts
54. scale provider implementations
55. optional SAM2 workstream — non-blocking
```

## Phase M2 — Dense

```text
56. COLMAP undistort
57. PatchMatch capability/compute preflight
58. PatchMatch
59. fusion
60. provider-native evidence model
61. canonical dense evidence adapter
62. dense report
63. dense gate
```

## Phase M3 — Mesh + SoftSight

```text
64. mesh provider abstraction
65. Poisson
66. Delaunay
67. AdvancingFront
68. reconstruction package builder
69. package seal/publish
70. SoftSight provider client
71. SoftSight reconstruction QA
72. verdict/execution interpretation
73. mesh candidate eligibility
74. mesh candidate scoring
75. reconstruction tournament
```

## Phase M4/M5 — Production

```text
76. Blender provider
77. production provenance transition rules
78. master asset
79. texturing
80. LOD
81. collision
82. GLTFAdapter transform boundary
83. transform-gltf-v1 fixture
84. master GLB
85. meshoptimizer / gltfpack
86. KTX2
87. glTF Validator
88. production package builder
89. production package seal/publish
90. SoftSight production QA
91. final report
```

## Phase M6 — Product intelligence + hardening

```text
92. Capture Advisor capability-aware
93. rescan lineage
94. benchmark suite
95. high-level presets
96. integration tests
97. operational hardening
98. cross-platform contract parity
99. release hardening
100. V1.0
```

## Explicitly non-blocking for V1 core

```text
OpenMVSProvider
ALIKED/LightGlue
Gaussian
remote compute
desktop UI
```

---

# 69. Commit strategy

No commits enormes.

Ejemplos:

```text
chore(core): initialize project architecture
```

```text
feat(domain): add project and artifact models
```

```text
feat(pipeline): add deterministic stage state machine
```

```text
feat(media): add ffmpeg inspection provider
```

```text
feat(capture): add frame quality metrics
```

```text
feat(capture): add smart frame selector v1
```

```text
feat(colmap): add sparse reconstruction provider
```

```text
feat(dense): add colmap patchmatch provider
```

```text
feat(mesh): add poisson mesh candidate
```

```text
feat(softsight): add reconstruction QA provider
```

---

# 70. Gate policy V1.1

Cada milestone:

```text
implementation
+
unit tests
+
integration fixture
+
contract/schema checks where relevant
+
docs
+
benchmark where relevant
```

No avanzar si:

```text
mypy fails
ruff fails
tests fail
schema generation/check fails
provider contract unstable
artifact schema ambiguous
package integrity fails
R0-B required gate fails
```

P12:

```text
una medida y una prueba que falla tienen más autoridad
que más prosa de arquitectura
```

---

# 71. Testing pyramid V1.1

## Unit

```text
domain
strict serialization
hashing
path sandbox
package sealing
CameraSet
FrameGraph
Scale
cache
selectors
metrics
contracts
```

## Contract fixtures

```text
cube-v1
unknown-field-v1
invalid-path-v1
hash-mismatch-v1
camera-transform-v1
image-orientation-v1
unknown-capability-v1
unsealed-package-v1
transform-gltf-v1
```

## Cross-project parity

```text
SoftSight ↔ expected.json
VideoMesh ↔ expected.json
SoftSight ↔ VideoMesh
```

Solo shared boundary facts. No duplicar SoftSight-owned QA.

## Integration

```text
FFmpeg
COLMAP sparse
SoftSight client
Blender provider
glTF validator
```

## End-to-end

```text
small fixture video
→
asset
```

## Benchmark

```text
large datasets
real turret
performance/resource gates
```

---

# 72. Fixtures E2E

V1.1 distingue dos fixtures obligatorios.

## Contract E2E — `cube-v1`

Vive en Foundation.

Objetivo:

```text
prove canonical package + SoftSight boundary
```

No necesita video ni calidad fotogramétrica.

## Pipeline E2E — `small-video-v1`

Objeto sintético/simple y video pequeño.

Objetivo:

```text
test entire product DAG
```

No sustituye `cube-v1` y no se usa para definir convenciones contractuales.

---

# 73. Real E2E fixture

Nuestra torreta.

Será benchmark principal de mechanical asset.

---

# 74. Documentation required

```text
ARCHITECTURE.md
PROVIDERS.md
PROJECT_FORMAT.md
PIPELINE.md
CAPTURE_GUIDE.md
SOFTSIGHT_CONTRACT.md
CONTRACT_COMPATIBILITY.md
CAMERA_AND_FRAME_CONVENTIONS.md
PACKAGE_FORMAT.md
BENCHMARKS.md
TROUBLESHOOTING.md
LICENSES.md
```

`SOFTSIGHT_CONTRACT.md` debe apuntar al registro canónico, no duplicar decisiones con redacción divergente.

---

# 75. Architecture Decision Records

Crear ADRs para:

```text
Python as core language
provider architecture
COLMAP as V1 reconstruction engine
SoftSight as QA/certification layer
filesystem package handoff
strict schema + schema hash compatibility
sealed immutable packages
canonical CameraSet
FrameGraph + transform algebra
ScaleStatus/ScaleSource split
artifact-bound provenance
PLY+JSON+EXR reconstruction evidence contract
GLB production format + GLTFAdapter boundary
SQLite metadata
local-first
```

Los ADRs explican el porqué; no reemplazan el registro contractual SoftSight ↔ VideoMesh.

---

# 76. Definition of professional quality

VideoMesh no es profesional porque tenga UI bonita.

Es profesional cuando:

```text
failure is explainable
results are measurable
runs can resume
artifacts are traceable
providers are replaceable
outputs are validated
benchmarks exist
contracts are versioned
```

---

# 77. Final V1 acceptance test

Input:

```text
turret_orbit.mp4
```

Command:

```bash
videomesh build turret_orbit.mp4 \
  --capture object-orbit \
  --quality high \
  --target web
```

Preconditions:

```text
requested providers compatible
required compute capabilities available
SoftSight contract/schema compatible
```

Debe producir:

```text
Contract R0-B                 PASS
Capture                       PASS
Frames                        PASS
SfM                           PASS
Camera/Frame normalization    PASS
Scale                         PASS / EXPLICIT UNKNOWN where target permits
Dense                         PASS
Mesh                          PASS
SoftSight Reconstruction      COMPLETE + PASS
Production                    PASS
LOD                           PASS
Textures                      PASS
GLB                           PASS
glTF Validator                PASS
SoftSight Production          COMPLETE + PASS

FINAL
PRODUCTION_READY
```

Si el hardware/preset no puede ejecutar una fase:

```text
UNSUPPORTED
```

con razón tipada; nunca simular éxito.

---

# 78. Final architectural rule

```text
VideoMesh
=
ORCHESTRATE
+
RECONSTRUCT
+
COMPILE

SoftSight
=
MEASURE
+
PROVE
+
CERTIFY
```

No mezclar.

---

# 79. V1 technical stack frozen

```text
Core:
Python

Contracts:
strict JSON + JSON Schema boundary + SHA-256

Media:
FFmpeg

Frame intelligence:
OpenCV + VideoMesh algorithms

Masks:
None / Manual core
SAM2 optional

SfM:
COLMAP incremental/global

Dense:
COLMAP PatchMatch provider

Meshing:
COLMAP Poisson/Delaunay/AdvancingFront

Geometry QA:
SoftSight

Production:
Blender Provider

Optimization:
meshoptimizer / gltfpack

Texture compression:
BasisU / KTX2

Validation:
Khronos glTF Validator + SoftSight
```

Compute availability is capability-driven. A frozen stack does not mean every machine can execute every provider.

---

# 80. V1 product promise

VideoMesh V1 debe poder decir:

> Dame una captura válida y un conjunto de providers/compute capaces de ejecutar el preset solicitado, y VideoMesh producirá una reconstrucción 3D medida, trazable, optimizada y validada, o explicará de forma tipada por qué no puede ejecutarla o certificarla.

No prometer:

```text
perfect reconstruction from any video
full dense reconstruction on unsupported compute
PASS when evidence is insufficient
```

Prometer:

```text
measured reconstruction from valid capture
explicit capability handling
explicit uncertainty
artifact-bound certification
```

---

# 81. Resultado final del roadmap V1.1

La ruta correcta es:

```text
Contract Foundation
   ↓
cube-v1
   ↓
SoftSight R0-B
   ↓
Core Foundation
   ↓
Canonical Media
   ↓
Sparse
   ↓
CameraSet + FrameGraph
   ↓
Scale Resolution
   ↓
Smart Capture
   ↓
Dense
   ↓
Mesh
   ↓
Sealed Reconstruction Package
   ↓
SoftSight QA
   ↓
Tournament
   ↓
Production
   ↓
GLB
   ↓
Optimization
   ↓
Sealed Production Package
   ↓
Final Certification
```

Orden de prioridades obligatorio:

```text
prove contract first
then build product pipeline
```

---

# 82. Milestones principales V1.1

## M0-A

```text
VideoMesh Contract Foundation PASS
```

## M0-B

```text
cube-v1 → SoftSight R0-B PASS
```

## M0-C

```text
Project/Pipeline Engine stable
```

## M1

```text
Video → Sparse + canonical CameraSet
```

## M2

```text
Video → Dense
```

## M3

```text
Video → Sealed Reconstruction Package → Verified Mesh
```

## M4

```text
Video → Textured Asset
```

## M5

```text
Video → Validated Production GLB
```

## M6

```text
Video → Sealed Production Package → Production Certified
```

## M7

```text
V1.0
```

---

# 83. No-advance rule V1.1

No saltar etapas.

Especialmente:

```text
NO FFmpeg/COLMAP product work before contract R0-B
   except independent non-contract benchmarking/tooling

NO SoftSight QA on mutable directories

NO coverage/confidence assumptions before
CameraSet + FrameGraph + visibility semantics are proven

NO production UI before engine stable

NO AI providers before V1 pipeline stable

NO cloud before local resume/cache stable

NO automatic hallucination before provenance is implemented

NO Gaussian in V1 required path
```

Si R0-B falla por:

```text
schema
camera projection
matrix convention
artifact identity
package security/hash
```

corregir frontera antes de avanzar trabajo dependiente del contrato.

---

# 84. First execution plan for the CLI agent — V1.1

Los sprints describen orden lógico, no duración de calendario.

## Sprint 0A — Contract primitives

```text
repository skeleton
CI foundation
strict JSON serializer
schema boundary
documentType/version/hash
Artifact model
discriminated artifact schema
purelyReconstructed
```

## Sprint 0B — Camera / Scale / Frames

```text
CameraSet
CameraImageSpace
canonical orientation
named distortion
FrameGraph
transform algebra
ScaleStatus/Source/uncertainty
MeasurementClass
ReproducibilityMode
capabilities
```

## Sprint 0C — Package integrity

```text
packageId
sandbox
bytes + SHA256
atomic same-filesystem sealing
unknown-field fixture
invalid-path fixture
hash-mismatch fixture
unsealed-package fixture
```

## Sprint 0D — Contract vertical slice

```text
cube-v1 generator
expected.json
VideoMesh parity harness
SoftSight handshake
R0-B PASS
```

**No empezar Sprint 1 hasta R0-B PASS.**

## Sprint 1 — Core engine

```text
project manifest
SQLite
stage state machine
pipeline DAG
cache
resume
structured logs
CLI init/status/doctor
```

## Sprint 2 — Media

```text
FFmpeg provider
media inspection
canonical orientation
frame extraction
frame quality v1
```

## Sprint 3 — Sparse

```text
smart selector v1
COLMAP sparse provider
ColmapAdapter
canonical CameraSet
FrameGraph population
SfM report/gate
```

## Sprint 4 — Capture intelligence

```text
selector benchmark
smart selector v2
none/manual masks
calibration providers
scale providers
SAM2 optional parallel workstream
```

## Sprint 5 — Dense

```text
compute/capability preflight
COLMAP dense
native evidence
canonical evidence adapter
dense report/gate
```

## Sprint 6 — Mesh + sealed reconstruction

```text
mesh candidates
reconstruction package
seal/publish
SoftSight integration
ExecutionStatus/CertificationVerdict handling
reconstruction gate
```

## Sprint 7 — Tournament

```text
candidate eligibility
candidate scoring
tournament
```

## Sprint 8 — Production foundation

```text
Blender provider
production provenance rules
master asset
texturing
```

## Sprint 9 — Runtime assets

```text
LOD
collision
GLTFAdapter
transform-gltf-v1
master GLB
meshoptimizer
KTX2
```

## Sprint 10 — Final validation

```text
glTF validation
production package
seal/publish
SoftSight production QA
final report
```

## Sprint 11 — Advisor + operational hardening

```text
Capture Advisor
rescan lineage
crash recovery
cache/invalidation audit
resource metrics
```

## Sprint 12 — Benchmarks + release

```text
synthetic benchmark
real turret benchmark
cross-platform parity
nightly/GPU CI expansion
docs
release hardening
V1.0
```

---

# 85. Success criteria V1.1

VideoMesh V1 será exitoso si:

```text
1. cube-v1 prueba la frontera SoftSight ↔ VideoMesh antes de fotogrametría;
2. una captura válida puede procesarse end-to-end cuando el compute/preset es soportado;
3. cada stage puede reiniciarse independientemente;
4. una falla no obliga a repetir todo;
5. cada artifact tiene identidad por bytes + SHA256 y provenance;
6. TRIANGLE_MESH declara purelyReconstructed de forma estricta;
7. CameraSet/FrameGraph eliminan ambigüedad de backend;
8. Scale UNKNOWN/RELATIVE/ABSOLUTE se maneja sin inventar unidades;
9. packages entregados a SoftSight son sandboxed, SEALED e inmutables;
10. SfM/MVS no están acoplados al dominio;
11. SoftSight es la fuente de verdad geométrica/certificación;
12. ERROR, FAIL e INCONCLUSIVE nunca se confunden;
13. GLB final pasa Khronos validation;
14. final readiness requiere SoftSight COMPLETE + PASS;
15. benchmarks son reproducibles según el modo declarado;
16. CLI puede operar sin UI;
17. capability incompatibility falla temprano y de forma explicable;
18. V2 puede añadir nuevos providers/representations sin reescribir el core.
```

---

# 86. Conclusión V1.1

La forma correcta de construir VideoMesh no es implementar un enorme sistema de fotogrametría propio.

Debemos construir una **capa de producto, contratos e inteligencia** alrededor de backends maduros:

```text
FFmpeg
OpenCV
COLMAP
SoftSight
Blender
meshoptimizer
KTX2
glTF Validator
```

Pero V1.1 añade una regla fundamental que el roadmap original todavía no tenía:

```text
NO construir primero y acordar la frontera después.

PROBAR LA FRONTERA PRIMERO.
```

El valor propio estará en:

```text
Canonical Contract Boundary
Artifact Identity + Provenance
CameraSet + FrameGraph
Scale semantics
Smart Frame Intelligence
Capture Intelligence
Project Model
Pipeline Engine
Provider Architecture
Reconstruction Tournament
Quality Intelligence
SoftSight Certification
Capture Advisor
Cache / Resume
Production Compiler
```

El objetivo final:

```text
VIDEO
   ↓
CANONICALIZE
   ↓
MEASURE
   ↓
RECONSTRUCT
   ↓
PACKAGE + SEAL
   ↓
VERIFY
   ↓
REFINE
   ↓
OPTIMIZE
   ↓
PACKAGE + SEAL
   ↓
VALIDATE
   ↓
CERTIFY
   ↓
PRODUCTION ASSET
```

Este documento V1.1 reemplaza el orden de implementación del roadmap V1 original y es el documento que debe recibir el agente CLI para comenzar VideoMesh.

La primera victoria esperada no es COLMAP.

Es:

```text
cube-v1
↓
SoftSight R0-B
↓
PASS
```

Después de eso empieza la reconstrucción real.

