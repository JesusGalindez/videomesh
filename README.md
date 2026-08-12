# VideoMesh V1.1 — Canonical Diagram System

**First-pass scope:** VM-D00, VM-D02, VM-D03, VM-D04, VM-D05, VM-D06, VM-D07 only.

These diagrams are visual views over the canonical sources. They do not create architecture decisions.

| ID | File | Type | Question | Sources | Status |
|---|---|---|---|---|---|
| VM-D00 | `00-system-context` | Architecture | What is VideoMesh and what surrounds it? | V1.1 roadmap + canonical contract | CURRENT VIEW |
| VM-D02 | `02-r0-contract-bootstrap` | Flowchart | Why does product implementation wait for R0-B? | V1.1 roadmap + canonical contract | CURRENT VIEW; Sprint 0A is CURRENT, not complete |
| VM-D03 | `03-core-layers` | Layer stack | What may depend on what? | V1.1 roadmap | CURRENT VIEW |
| VM-D04 | `04-domain-artifact-model` | ER / data model | What are the core information objects? | V1.1 roadmap + canonical contract | CURRENT VIEW |
| VM-D05 | `05-camera-frame-scale` | Architecture | How does backend camera data become canonical geometry context? | V1.1 roadmap + canonical contract | CURRENT VIEW |
| VM-D06 | `06-package-lifecycle` | State machine | When is a package valid for SoftSight? | V1.1 roadmap + canonical contract | CURRENT VIEW |
| VM-D07 | `07-softsight-sequence` | Sequence | How is a report bound to exact package/artifact bytes? | V1.1 roadmap + canonical contract | CURRENT VIEW |

## Navigation

```text
VM-D00 System Context
  ├─ VM-D02 R0 Contract Bootstrap
  │    └─ VM-D03 Core Layers
  │         └─ VM-D04 Domain Model
  │              └─ VM-D05 Camera / Frame / Scale
  └─ VM-D06 Package Lifecycle
        └─ VM-D07 SoftSight Sequence
```

## Formats

- `html/` — canonical editable/render source: standalone HTML with inline SVG and no JavaScript.
- `svg/` — derived by extracting the inline SVG from the HTML source.
- `png/` — 2560×1440 raster derived from the extracted inline SVG because local Chromium navigation is blocked in this execution environment.

## Reserved next diagrams — not generated in this pass

VM-D01, VM-D08, VM-D09, VM-D10, VM-D11, VM-D12, VM-D13.

## Optional future views — not V1 dependencies

VM-D20 Capture Advisor; VM-D21 Reconstruction Tournament; VM-D22 Cache / Resume; VM-D23 Compute Capabilities; VM-D24 Production Certification; VM-D30 Digital Twin; VM-D31 Appearance Twin / Gaussian; VM-D32 Mechanical Twin; VM-D33 Physical Twin.

## Source hierarchy

```text
code / executable schemas
        ↓
canonical contracts
        ↓
ADRs
        ↓
VIDEOMESH_V1_1_IMPLEMENTATION_ROADMAP.md
        ↓
diagrams
```

**Rule:** diagrams are views, not sources of truth.
