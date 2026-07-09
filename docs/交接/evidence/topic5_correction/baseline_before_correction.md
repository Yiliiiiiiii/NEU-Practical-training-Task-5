# 课题 5 纠偏前基线

- branch: fix/topic5-config-driven-correction
- baseline_commit: 07dabd39883b3913368a09fa0c87b53521d13d9c
- verify_all: passed
  - command: `backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`
  - result: `739 passed`; backend ruff passed; frontend build passed; OpenAPI exported to `docs\openapi.json`
- frontend_tests: passed
  - command: `npm.cmd test` in `frontend`
  - result: `8 passed`, `24 passed`
- regression_gates: passed with current script arguments
  - command: `backend\.venv\Scripts\python.exe scripts\check_regression_gates.py --metrics reports\evaluation_center\current_metrics.json --gates reports\evaluation_center\regression_gates.json --out reports\evaluation_center\regression_gate_report.json`
  - result: `6/6` gates passed
- baseline_command_note:
  - document command `backend\.venv\Scripts\python.exe scripts\check_regression_gates.py` failed because the current script requires `--metrics` and `--gates`.
- 当前已知问题：
  1. Schema/Template 主要从本地 catalog 加载，未突出“运行时输入配置”。
  2. SchemaRouterService 硬编码 5 类 schema family。
  3. CandidateService 含较多领域规则。
  4. README / requirement_mapping 需要把 5 类 SchemaPack 降级为 examples。
