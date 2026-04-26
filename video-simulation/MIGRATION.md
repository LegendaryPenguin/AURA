# Migration Notes

## Modes

- New staged mode (default): `--pipeline-mode staged`
- Legacy compatibility mode: `--pipeline-mode compat` or `--compat-mode`

## Rollback Toggle

If staged mode fails validation or runtime checks, run:

```bash
python pipeline/run_pipeline.py --image <path> --pipeline-mode compat
```

This restores previous OCR + heuristic behavior.

## Safety Guarantees

- `verify` stage never sets `is_verified: true` unless symbolic checks pass.
- If SymPy is unavailable or parsing fails, output is marked draft with uncertainty reasons.
- Stage outputs are schema-validated via `video-simulation/schemas/*.schema.json`.

## Recommended Cutover

1. Run staged mode with `--skip-render` on your sample set.
2. Run tests in `video-simulation/tests/`.
3. Compare outputs with `eval/ab_compare.py`.
4. Keep compatibility mode available until staged quality is stable across your dataset.
