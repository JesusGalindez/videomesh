# Validation — VideoMesh V1.1 diagrams first pass

Validated: 2026-08-12

## Automated checks

All seven HTML diagram sources pass:

- no JavaScript `<script>` blocks;
- one inline SVG per file;
- SVG `role="img"`;
- resolving `aria-labelledby`;
- non-empty `<title>` as first SVG child;
- non-empty `<desc>` as second SVG child;
- `viewBox="0 0 1280 720"`;
- inline SVG style definitions preserved for standalone SVG export;
- no diagonal `<line>` connector between off-axis endpoints;
- every multi-segment orthogonal connector uses rounded `Q` elbows;
- no Unicode arrow glyph used as a substitute for a connector;
- diagram layout attributes follow the 4px grid.

## Visual inspection

Reviewed PNG renders for:

- clipping;
- label collisions;
- node overlap;
- connector legibility;
- connector-to-box ambiguity;
- footer separation;
- focal hierarchy;
- consistent VideoMesh / SoftSight visual semantics.

No blocking visual defect remains in the first-pass set.

## Export status

- HTML: PASS — canonical source.
- SVG: PASS — extracted from the canonical inline SVG in HTML.
- PNG: PASS — 2560×1440. Local Chromium navigation is blocked by the execution environment, so PNG was rasterized from the derived inline SVG with CairoSVG rather than browser screenshotting.

This rendering fallback changes the export mechanism, not the diagram content or architecture semantics.
