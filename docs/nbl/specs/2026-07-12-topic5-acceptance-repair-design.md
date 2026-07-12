# Topic 5 Acceptance Repair Design

## Goal

Make the exact repository head reproducibly satisfy the Topic 5 assignment requirements in clean Windows and Linux checkouts, and ensure the published acceptance status reflects the actual gate result.

## Scope

The repair is limited to the six findings from the 2026-07-12 audit:

1. Cross-platform frozen evaluation assets and clean-checkout failures.
2. Verification-runner failure reporting.
3. Content-tag accuracy acceptance semantics.
4. Reproducible LLM difficult-mapping evidence.
5. Exact-head status and handoff documents.
6. A per-capability implementation/data/performance/cost matrix.

Raw-document parsing, production blind claims, Topic 6 scoring, and automatic LLM acceptance remain out of scope.

## Design

Frozen text and JSON evaluation assets will use repository-enforced LF endings. Hash manifests continue to validate bytes, so corruption detection remains strict without depending on a developer's Git configuration.

The verification runner will treat every command as evidence. It will always write a summary, will not read a missing final gate, and will expose the failing command and error in the machine report. The final gate will consume freshly generated evaluator reports only.

Tag evaluation will report both label-level exact accuracy and precision/recall/F1. The assignment gate will require content-tag accuracy of at least 0.85 and retain F1 as a diagnostic. Management scope, trace correctness, and unknown tags will become explicit non-regression checks.

LLM evidence will use the deterministic fallback adapter in CI to exercise a genuinely ambiguous candidate choice, confidence, evidence, and mandatory review behavior. Live provider evidence remains optional and no LLM output may be auto-accepted.

Status documents will be regenerated from exact-head verification output. The capability matrix will document implementation type, input form, cost/performance characteristics, and why deterministic processing is sufficient where applicable.

## Verification

- Clean checkout: all backend tests pass.
- Frontend tests and build pass.
- Frozen mapping and replay evaluators reproduce on Windows line endings and LF-only checkouts.
- A deliberately failing final-gate command still produces a valid verification summary.
- Tag gate checks accuracy, scope, trace, and unknown-tag constraints.
- LLM difficult-mapping evaluator proves review-only behavior with nonzero evaluated cases.
- Full `scripts/run_topic5_batch_2_verification.py` passes in simulated exact-head CI mode.

