# Global Alignment Governance

This document defines the enforcement model that keeps roadmap claims, task claims, runtime behavior, and verification evidence aligned.

## Purpose

- Prevent global planning/runtime drift.
- Prevent false `Done` or phase-complete claims.
- Keep execution low-friction via checklist-first operations.

## Governing Principle

A claim is only valid when **verification evidence** proves **runtime behavior** satisfies **contract requirements** and produces **capability outcomes**.

## Truth Layers

1. **Capability truth**: user-visible behavior by phase.
2. **Contract truth**: schemas/interfaces/route payload shape guarantees.
3. **Runtime truth**: config/env/scripts/app defaults and actual route/pipeline support.
4. **Verification truth**: tests/manual checks and artifacts proving behavior.

## Maturity Model

- `Planned`
- `Implemented`
- `Integrated`
- `Verified`
- `DemoReady`

### Promotion Rules

- No skipping maturity levels.
- Promotion beyond `Implemented` requires evidence.
- Any post-promotion regression forces rollback by at least one level.

## Checklist-First Operating Model

`WORKFLOW_CHECKLIST.md` is the only required day-to-day execution guide.

### Mandatory Start Gates

- Task template sections exist.
- `MaturityBefore` is recorded.
- target maturity is declared.
- dependencies are acknowledged.

### Mandatory End Gates

- verification and dependency closure completed for target maturity.
- required completion fields present.
- explicit outcome: `Promote` or `DoNotPromote`.
- rollback path executed when needed.

## Required Completion Fields

- `MaturityBefore`
- `MaturityAfter`
- `DependenciesClosed`
- `EvidenceLinks`
- `ResidualRisk`
- `RollbackRequired` (`Yes`/`No`)
- `PromotionOutcome` (`Promote`/`DoNotPromote`)
- `EvidenceEnvironment` (`Mock`/`CI-TestClient`/`On-device edge`)
- `HardwareProfile`

If any required field is missing, result is `DoNotPromote`.

## Cross-File Alignment Checks

Before promotion to `Verified` or above:

1. **Roadmap <-> task files**
  - phase status does not exceed required task maturity.
2. **Task files <-> checklist**
  - task sections and checklist gates are consistent.
3. **Roadmap <-> runtime**
  - phase definitions match implemented routes/pipelines or explicitly mark gaps.
4. **Config <-> scripts <-> env docs**
  - canonical names/paths agree across `config/*.yaml`, startup scripts, and `.env.example`.
5. **Contracts <-> tests**
  - each public route has matching route-boundary contract test coverage.

## Promotion Evidence Template

Use this block for every maturity promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: <TASK_ID>
  MaturityBefore: <level>
  MaturityAfter: <level>
  ChangeSummary: <what changed>
  GatesRun:
    - <test/check>
  EvidenceLinks:
    - <path/url/log>
  DependenciesClosed: <yes/no + note>
  ResidualRisk: <risk + owner>
  RollbackRequired: <Yes/No>
  PromotionOutcome: <Promote|DoNotPromote>
  EvidenceEnvironment: <Mock|CI-TestClient|On-device edge>
  HardwareProfile: <device/runtime profile>
  Signoff:
    - <workstream/owner>
```

## Exception and Rollback Policy

- If a required gate fails: `DoNotPromote`.
- If regression is discovered after promotion:
  - lower maturity immediately,
  - record blocker and owner,
  - define re-promotion criteria.

## Migration Policy

For legacy tasks during rollout:

- retain `Status` for compatibility.
- add `Maturity` on next task touch.
- if `Status: Done` but incomplete gates, set `Maturity` to proven level and add migration note.

## Success Criteria

Governance rollout is successful when:

- roadmap phase claims never exceed proven maturity gates,
- contributors can execute using checklist prompts only,
- promotion decisions are evidence-backed and reproducible,
- regressions trigger rollback consistently.

