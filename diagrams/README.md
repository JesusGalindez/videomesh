# VideoMesh V1.1 — Canonical Diagram System

**Status:** complete canonical V1.1 visual set, VM-D00 through VM-D13 (with the intentional numbering defined by the diagram plan).

These diagrams are views over code/schemas/contracts/ADRs/roadmap. They do not create architecture decisions.

| ID | File | Type | Question |
|---|---|---|---|
| VM-D00 | `00-system-context` | Architecture | What is VideoMesh and what surrounds it? |
| VM-D01 | `01-v1-pipeline` | Data Flow | How does valid capture become a certified production asset? |
| VM-D02 | `02-r0-contract-bootstrap` | Flowchart | Why does product implementation wait for R0-B? |
| VM-D03 | `03-core-layers` | Layer Stack | What may depend on what? |
| VM-D04 | `04-domain-artifact-model` | ER / Data Model | What are the core information objects? |
| VM-D05 | `05-camera-frame-scale` | Architecture / Data Model | How does backend camera data become canonical geometry context? |
| VM-D06 | `06-package-lifecycle` | State Machine | When is a package valid for SoftSight? |
| VM-D07 | `07-softsight-sequence` | Sequence | How is a report bound to exact package/artifact bytes? |
| VM-D08 | `08-provider-topology` | Architecture | Which replaceable providers implement VideoMesh ports? |
| VM-D09 | `09-stage-dag-overview` | Data Flow / Architecture | What are the major execution boundaries? |
| VM-D10 | `10-reconstruction-dag` | Data Flow | How does evidence become a certified raw mesh? |
| VM-D11 | `11-production-dag` | Data Flow | How does a verified mesh become a certified runtime asset? |
| VM-D12 | `12-determinism-model` | Architecture / Concept Map | What are the three determinism concepts? |
| VM-D13 | `13-v1-implementation-roadmap` | Gantt / Roadmap | What is the logical implementation order to V1.0? |

## Navigation

```text
VM-D00 System Context
  └─ VM-D01 Product Pipeline
       ├─ VM-D08 Provider Topology
       └─ VM-D09 Stage DAG Overview
            ├─ VM-D10 Reconstruction DAG
            └─ VM-D11 Production DAG

VM-D02 R0 Contract Bootstrap
  └─ VM-D03 Core Layers
       └─ VM-D04 Domain + Artifact Model
            └─ VM-D05 Camera / Frame / Scale

VM-D06 Package Lifecycle
  └─ VM-D07 SoftSight Handoff

VM-D12 Determinism + Metrics — cross-cutting semantic view
VM-D13 V1.1 Roadmap — implementation-order view
```

## Formats

- `html/`: canonical standalone HTML views with inline SVG and no JavaScript.
- `svg/`: vector versions.
- `png/`: 2560×1440 raster versions.

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
