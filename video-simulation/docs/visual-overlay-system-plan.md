# Visual Overlay System Plan (Magic Equation Correction)

## Goal

Design a reusable overlay system that can animate math-equation correction steps over tutorial frames/videos, producing a clear "magical correction" effect while preserving legibility and timing accuracy.

## Source Asset

- Equation screenshot for this workflow:
  - `video-simulation/assets/math-equations/magic-equation-correction-source.png`

## Scope

- Input: static equation image and/or extracted equation states from narration/pipeline.
- Output: rendered overlays in GIF/MP4 that show:
  - step highlights,
  - transformed equation lines,
  - optional glow/particle accents,
  - final corrected expression.

## Architecture

- **Overlay Spec Layer**
  - Define a JSON schema for overlay events: text, bbox/anchor, style, start/end timestamps, easing.
  - Keep it renderer-agnostic so fallback and high-fidelity renderers share the same event stream.

- **Layout & Anchoring Layer**
  - Support pixel and relative coordinates.
  - Add safe-area constraints to avoid clipping on different aspect ratios.
  - Include collision handling for multi-line equations and annotation labels.

- **Animation Layer**
  - Core transitions: fade, write-on, morph-replace, highlight pulse, sparkle trail.
  - Deterministic timing map for each correction step (e.g., combine-like-terms, isolate variable, simplify fraction).
  - Keep a single timeline clock used by all effects to prevent drift.

- **Rendering Layer**
  - Primary path: composited overlays on generated frames.
  - Fallback path: minimal text + bbox/highlight if advanced effects are disabled.
  - Export to both GIF and MP4 with matching frame timing.

## Data Model (Draft)

- `OverlayEvent`
  - `id`, `kind` (`text|shape|effect`)
  - `content` (equation fragment, annotation)
  - `anchor` (`x`, `y`, `w`, `h`, `mode`)
  - `style` (font, color, stroke, glow)
  - `timing` (`t_start_ms`, `t_end_ms`, `easing`)
  - `z_index`
- `CorrectionStep`
  - `step_id`, `input_expr`, `output_expr`, `reason`
  - `linked_events[]`

## Implementation Phases

1. **Phase A — Overlay Spec + Static Placement**
   - Add schema + parser for timeline events.
   - Render static equation annotations from the new source screenshot.

2. **Phase B — Core Transition Effects**
   - Implement write-on + highlight pulse + fade transitions.
   - Validate frame-accurate event timing in both GIF and MP4 outputs.

3. **Phase C — Magical Effects**
   - Add optional sparkle trail and glow-bloom effects behind transformed terms.
   - Add quality toggles for low/medium/high render modes.

4. **Phase D — Pipeline Integration**
   - Wire overlay generation into `video-simulation/pipeline/run_pipeline.py`.
   - Ensure fallback renderer consumes same timeline contract.

## Verification Plan

- Unit tests:
  - overlay event schema validation,
  - anchor-to-pixel mapping determinism,
  - timeline ordering and no-overlap invariants.
- Golden tests:
  - compare expected overlay sequence for one canonical equation correction.
- Visual QA:
  - verify legibility on light/dark backgrounds and across 16:9 + 9:16 outputs.

## Risks & Mitigations

- **Risk:** visual clutter reduces readability.
  - **Mitigation:** enforce contrast and maximum simultaneous effect count.
- **Risk:** timing drift between narration and overlays.
  - **Mitigation:** use a single timeline source and frame-locked scheduling.
- **Risk:** expensive effects slow rendering.
  - **Mitigation:** quality presets and fallback renderer parity.

## Next Actions

1. Define `overlay_event` schema in `video-simulation/schemas/`.
2. Add a small canonical event file for the equation screenshot.
3. Implement renderer hooks with feature flags for magical effects.
