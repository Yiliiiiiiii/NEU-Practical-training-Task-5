# Phase 7 实施计划：成果包与一致性校验

## 分支
`phase7-package-validation`（从 `e4ee31c` 创建）

## 基线
108 passed, ruff clean

## 任务清单

### 7.1 SchemaValidator — 内容校验引擎
- 文件：`validators/content_validator.py`（新建）
- 职责：校验 `content.json.data` 是否符合 TargetSchema
- 检查项：required、type（string/integer/float/bool/date/array/object）、enum、pattern、min_length/max_length
- 输出：`ValidationReport`（复用 schemas/reports.py）
- 测试：`tests/test_content_validator.py`
  - required 缺失 → error issue
  - type 不匹配 → warning issue
  - enum 未命中 → error issue
  - pattern 不匹配 → warning issue
  - 全部通过 → passed=True

### 7.2 ConsistencyValidator — 跨格式一致性
- 文件：`validators/consistency_validator.py`（新建）
- 职责：检查 content.json / content.md / chunks.json / canonical 之间的一致性
- 检查项：
  - block 顺序一致（json vs md vs canonical）
  - block_id 唯一且可回链
  - chunk source_blocks 可回链 canonical blocks
  - chunk 文本包含在 content 文本中
  - 资产引用可解析
- 输出：`ConsistencyReport`（复用 schemas/reports.py）
- 测试：`tests/test_consistency_validator.py`
  - 正常链路 → passed=True
  - 断开 chunk source_blocks → critical error, passed=False
  - 缺失 block → error

### 7.3 ManifestEngine — 文件清单生成
- 文件：`engines/manifest_engine.py`（新建）
- 职责：对 staging 目录中所有 payload 文件生成 Manifest
- 每条 ManifestFile：path、required、media_type、sha256(64位hex)、bytes(真实)、role
- 约束：不包含 manifest.json 自身，不包含 ZIP 本身，path 规范化
- 测试：`tests/test_manifest_engine.py`
  - SHA-256 与真实字节一致
  - 不包含自身
  - path 规范化（无绝对路径、无 ..）
  - 按 path 排序

### 7.4 PackageService — 打包编排
- 文件：`services/package_service.py`（新建）
- 编排顺序：
  1. 确认 content.json/content.md/chunks.json 已存在
  2. 生成 metadata.json、config_snapshot.json、mapping_report.json
  3. 运行 ContentValidator → validation_report.json
  4. 运行 ConsistencyValidator → consistency_report.json
  5. consistency 有 critical error → 阻止打包
  6. 运行 ManifestEngine → manifest.json
  7. 构建 ZIP（staging → 原子移动）
  8. 计算 ZIP SHA-256，保存到数据库
  9. 设置 package/task status=completed
- 数据库：OutputPackageRecord + PackageFileRecord
- 测试：`tests/test_package_service.py`
  - general demo 端到端打包
  - policy demo 端到端打包
  - consistency critical error 阻止打包
  - ZIP SHA-256 一致
  - 幂等/版本策略

### 7.5 API 路由
- 文件：`api/v1/tasks.py`（修改）
- 新增路由：
  - `POST /{task_id}/package` → PackageService.create_package
  - `GET /{task_id}/package/download` → FileResponse
  - `GET /{task_id}/reports/validation` → ValidationReport
  - `GET /{task_id}/reports/consistency` → ConsistencyReport
  - `GET /{task_id}/trace` → trace list
- API schemas：`schemas/api.py`（修改）
- 测试：`tests/test_package_api.py`
  - TestClient 真实请求所有 5 个 API
  - 404/409 状态码
  - download Content-Type=application/zip
  - SHA-256 响应头

### 7.6 真实链路测试
- 文件：`tests/test_phase7_e2e.py`
- general demo：UIR → schema → template → task → candidate → mapping → convert → package → download → unzip → 校验
- policy demo：同样链路，验证日期/enum/正文

### 7.7 README 更新
- 更新实现状态、API 列表、已知限制

## 提交边界
1. `docs: add phase 7 implementation plan` — 计划
2. `feat: add content validator, consistency validator, manifest engine` — 核心引擎
3. `feat: add package service and API routes` — service + API
4. `test: add phase 7 regression and e2e tests` — 测试
5. `docs: update README for phase 7` — 文档

## 完成标准
- 全量 pytest 通过
- Ruff clean
- git diff --check clean
- 手工验证：ZIP 下载、解压、Manifest SHA-256 校验
