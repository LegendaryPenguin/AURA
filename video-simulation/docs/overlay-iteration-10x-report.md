# Overlay Iteration Report (10x Auto-Execution)

## Objective

Run repeated end-to-end renders for the handwritten equation correction asset using a 3Blue1Brown-inspired pacing profile (`paper_3b1b`) and verify overlay-system readiness.

## Input

- Image: `video-simulation/assets/math-equations/magic-equation-correction-source.png`
- Manual steps fallback: `video-simulation/assets/math-equations/magic-equation-steps.json`
- Command profile:
  - `--style paper_3b1b`
  - `--preview`
  - `--manual-steps ...`

## Iteration Outputs

1. `video-simulation/outputs/tutorial_animation_20260425_194739.gif`
2. `video-simulation/outputs/tutorial_animation_20260425_194742.gif`
3. `video-simulation/outputs/tutorial_animation_20260425_194745.gif`
4. `video-simulation/outputs/tutorial_animation_20260425_194747.gif`
5. `video-simulation/outputs/tutorial_animation_20260425_194750.gif`
6. `video-simulation/outputs/tutorial_animation_20260425_194753.gif`
7. `video-simulation/outputs/tutorial_animation_20260425_194756.gif`
8. `video-simulation/outputs/tutorial_animation_20260425_194759.gif`
9. `video-simulation/outputs/tutorial_animation_20260425_194801.gif`
10. `video-simulation/outputs/tutorial_animation_20260425_194804.gif`

## QA Summary

Across all 10 runs, staged render QA returned `passed=true` with:

- ROI confident: true
- Equation near center: true
- Full line coverage: true
- Smooth timing profile: true
- Popup behavior (errors only): true

## Best Candidate

- Recommended output for review/demo: `video-simulation/outputs/tutorial_animation_20260425_194804.gif`
- Reason: latest successful run with full QA pass and stable anchor/timing checks.

## Notes

- Pipeline used GIF fallback because Manim/MP4 path was unavailable in this environment.
- Overlay plan baseline is documented at:
  - `video-simulation/docs/visual-overlay-system-plan.md`
