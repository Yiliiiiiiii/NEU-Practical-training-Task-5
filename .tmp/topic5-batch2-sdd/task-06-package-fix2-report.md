# Task 6 stored verifier identity follow-up

## Finding fixed

Final strict verification previously treated `verifier_report.json` as optional and checked only its manifest hash. Candidate package verification now explicitly opts out before the report exists; final strict verification requires the report and compares its complete canonical model to a fresh independent verification result.

## TDD evidence

- RED: deleting the stored report or changing its `passed`/`errors` fields both left strict verification passing (2 failed tests).
- GREEN focused: 3 passed.
- Package/API/registered/golden/compatibility regression matrix: 92 passed.
- Focused Ruff: passed.

The verifier report remains excluded from the manifest, avoiding a circular hash, while its full stored content is now validated against the manifest-bound independent result.
