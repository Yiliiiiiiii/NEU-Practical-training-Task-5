# Basic-stage Acceptance Matrix

## Current Mapping Metrics

- Dataset size: 50
- Auto mapping recall: 0.7774798927613941
- Assisted mapping recall: 0.806970509383378
- Review-required rate: 0.05714285714285714
- Required missing: 0
- Badcase violations: 0

| 要求 | 证据 | 状态 |
| --- | --- | --- |
| 输入 UIR / External UIR | external adapter eval、CLI/API demo | passed |
| Schema 驱动字段映射 | mapping eval、split eval | partial |
| 规则 + 大模型疑难映射 | DeepSeek suggestion eval | passed |
| 置信度与人工复核 | mapping report、review subagent report | passed |
| 分段、摘要、关键词 | content quality report | passed |
| JSON + Markdown 双形态 | package consistency report | passed |
| manifest/checksum | package verifier | passed |
| RAG/training/CSV 下游读取 | package consistency report | passed |
| 安全边界 | badcase、required missing、LLM auto accepted | passed |
