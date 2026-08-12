# VideoMesh Diagram Style Guide

**Status:** customized project skin for VideoMesh V1.1 canonical diagrams.

The skin follows `diagram-design` semantic roles and restraint: one or two focal accent elements, no shadows/glows, compact radii, orthogonal connectors, and mono only for technical labels.

| Role | Value | Use |
|---|---:|---|
| `paper` | `#111418` | page background |
| `paper-2` | `#181D23` | standard nodes |
| `paper-3` | `#20262E` | stores / activation |
| `ink` | `#F3F5F7` | primary text |
| `muted` | `#A7B0BB` | connectors / secondary text |
| `soft` | `#77828E` | metadata / sublabels |
| `rule` | `#2C343E` | hairlines / zones |
| `rule-solid` | `#46515E` | stronger borders |
| `accent` | `#E47A36` | VideoMesh focal role |
| `link` | `#7299C5` | SoftSight / external contract boundary |

## Typography

- Title: Instrument Serif; fallback Georgia / serif.
- Node names: Geist; fallback Inter / Arial / sans-serif.
- Technical labels: Geist Mono; fallback Menlo / Consolas / monospace.
- Font files are not bundled.

## Grammar

- 4px coordinate grid.
- No shadow, glow, or decorative gradient.
- Required paths are solid; optional/future paths are dashed.
- Off-axis connectors are orthogonal.
- Arrow labels have opaque masks and visible separation from strokes.
- VideoMesh owns the focal editorial accent. SoftSight uses the certification/link role.
- Diagrams are views, not sources of truth.
