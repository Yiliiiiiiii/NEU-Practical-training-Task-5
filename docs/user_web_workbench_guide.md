# SchemaPack Agent 网页工作台新手使用教程

这份教程写给第一次使用 SchemaPack Agent 的同学。你不需要懂后端、前端或 API，只要照着步骤操作，就可以把一份 UIR 文档导入系统，执行转换，并下载处理后的结果包。

## 你会完成什么

完成本教程后，你会知道如何：

- 启动网页工作台；
- 导入一份 UIR JSON 文档；
- 选择合适的 Schema 和 Template；
- 创建并执行 Task；
- 查看 Mapping、Validation、Chunk、Package 等结果；
- 下载 ZIP 结果包；
- 遇到常见问题时知道怎么处理。

## 先理解几个词

不用背，先有个印象就好：

| 词 | 你可以这样理解 |
| --- | --- |
| UIR | 系统能读懂的“规范化文档 JSON”。网页工作台处理的是 UIR，不直接处理 Word、PDF 或图片。 |
| Schema | 目标文档结构。比如政策文档、会议纪要、采购文档分别需要不同字段。 |
| Template | 字段映射规则。它告诉系统从 UIR 里找哪些内容，映射到 Schema 的哪些字段。 |
| Task | 一次处理任务。导入文档后，要创建 Task，再执行 Task。 |
| Mapping | 字段映射结果。表示系统把源文档里的内容对应到了哪些目标字段。 |
| Review | 需要人工确认的内容。系统不确定时不会强行自动通过，会放到 Review。 |
| Validation | 校验结果。检查生成内容是否符合 Schema 要求。 |
| Chunk | 切分后的文本片段，主要给检索、RAG 或训练数据使用。 |
| Package | 最终结果包，通常可以下载为 ZIP。 |

## 第一步：启动网页工作台

打开 PowerShell，进入项目目录：

```powershell
cd F:\p2
```

运行一键启动脚本：

```powershell
.\scripts\start_dev.ps1
```

正常情况下，它会打开两个新 PowerShell 窗口：

- 一个窗口运行后端 API；
- 一个窗口运行前端网页；
- 浏览器会自动打开 `http://127.0.0.1:5173/`。

如果没有自动打开浏览器，你可以手动访问：

```text
http://127.0.0.1:5173/
```

停止系统时，关闭那两个新打开的 PowerShell 窗口即可。

## 第二步：认识页面布局

网页大体分成左右两部分：

### 左侧：操作区

左侧主要用来输入和控制：

- 选择 `Schema`；
- 选择 `Template`；
- 设置 Chunk 策略；
- 粘贴或使用示例 UIR JSON；
- 点击“导入”“创建 Task”“执行”。

### 右侧：结果区

右侧主要用来看结果：

- 当前 Task 状态；
- Mapping 证据；
- Validation 问题；
- Chunk 证据；
- Package Manifest；
- 下游就绪度；
- Review 队列；
- Knowledge Packs。

## 第三步：使用示例 UIR

如果你只是想先跑通流程，建议先用页面自带示例。

在左侧点击：

```text
示例
```

页面下方的 `UIR JSON` 文本框会填入一份示例文档。

如果你已经有自己的 UIR JSON，也可以把自己的 JSON 粘贴到这个文本框里。

注意：这里必须是 UIR JSON，不是普通 Word、PDF、Excel 或图片。

## 第四步：选择 Schema 和 Template

页面左侧顶部有两个下拉框：

```text
Schema
Template
```

一般选择原则：

| 文档类型 | 推荐 Schema |
| --- | --- |
| 采购公告、采购结果、中标信息 | `procurement_doc` |
| 政策通知、政策办法、指南类文件 | `policy_doc` |
| 会议纪要、会议记录 | `meeting_doc` |
| 普通办事指南、服务指南、项目申报类文件 | `general_doc` |

选择 Schema 后，再选择同类 Template。通常名称里会带有类似：

```text
xxx_doc_base_v1
```

如果你不确定选哪个，先使用页面默认选项跑通流程。

## 第五步：导入文档

确认左侧 `UIR JSON` 文本框里有内容后，点击：

```text
导入
```

导入成功后，右侧顶部或指标区会出现文档 ID。通常会在“文档”一栏看到类似：

```text
real_policy_001_xxx
```

如果导入失败，常见原因是：

- JSON 格式不正确；
- 粘贴的不是 UIR；
- UIR 缺少必要字段，如 `uir_version`、`doc_id` 或 `blocks`。

## 第六步：创建 Task

导入成功后，点击：

```text
创建 Task
```

这一步会把当前文档、当前 Schema、当前 Template 和页面上的 Chunk 设置组合成一个处理任务。

成功后，右侧顶部会出现 Task ID。

## 第七步：执行 Task

创建 Task 后，点击：

```text
执行
```

系统会开始处理文档。处理内容包括：

- Mapping：字段映射；
- Transform：字段值规范化；
- Validation：校验；
- Content Organization：内容组织和 Chunk 切分；
- Package：生成结果包。

执行完成后，右侧各个结果面板会陆续显示内容。

## 第八步：查看核心结果

### 1. 看 Mapping 证据

查看：

```text
Mapping 证据
Mapping
```

你可以看到系统把哪些源字段映射到了哪些目标字段。

重点看：

- 已接受：系统比较确定的映射；
- 待 Review：系统认为需要人工确认的映射；
- 未映射：没有找到合适目标字段的内容。

如果待 Review 很多，不代表系统失败，而是说明这些字段存在歧义，需要人工确认或补充规则。

### 2. 看 Validation 问题

查看：

```text
Validation 问题
Validation
```

如果显示“已通过”，说明结构校验通过。

如果显示“需要处理”，通常说明：

- 必填字段缺失；
- 字段格式不符合要求；
- 生成结果需要人工 Review。

注意：Package 能生成，不等于所有字段语义都严格正确。Validation 和 Review 仍然要看。

### 3. 看 Chunk 结果

查看：

```text
Chunk 证据
Chunk 预览
```

Chunk 是系统把文档切成的小段文本，常用于：

- 检索；
- RAG；
- 训练语料；
- 下游内容消费。

你可以看到每个 Chunk 的来源、标签、摘要和切分策略。

### 4. 看 Package Manifest

查看：

```text
Package Manifest
Package
```

Package 是最终输出结果包。Manifest 会告诉你结果包里有哪些文件，比如：

- `content.json`
- `content.md`
- `chunks.jsonl`
- `mapping_report.json`
- `validation_report.json`
- `manifest.json`
- `verifier_report.json`

如果 Verifier 通过，说明结果包结构完整、文件哈希和必需产物校验通过。

## 第九步：下载 ZIP 结果包

当 Task 执行完成并生成 Package 后，在 `Package` 面板里会出现：

```text
下载 ZIP
```

点击后会下载一个 ZIP 文件。

这个 ZIP 就是本次处理结果，里面包含结构化 JSON、Markdown、Chunks、Mapping 报告、Validation 报告和 Manifest 等文件。

## 第十步：如何处理 Review 队列

如果页面出现 `Review 队列`，说明系统发现了一些不适合直接自动通过的映射。

你可以逐条查看：

- 源字段是什么；
- 目标字段是什么；
- 系统给出的置信度；
- Review 原因。

如果你确认这条映射是对的，可以点击：

```text
通过
```

如果你认为这条映射是错的，可以点击：

```text
拒绝
```

Review 的意义是：让系统不要为了“看起来指标更好”而乱自动接受低置信度结果。

## 第十一步：Knowledge Packs 是什么

`Knowledge Packs` 用于沉淀人工确认过的规则。

简单理解：

- Review 通过后，可以形成候选知识；
- 候选知识被接受后，可以创建 Pack；
- Pack 激活后，后续 Task 可以使用这些规则。

新手第一次使用时，可以先不操作 Knowledge Packs。等你熟悉 Review 后，再使用这部分能力。

## 推荐的新手操作顺序

第一次使用时，按这个顺序做：

1. 运行 `.\scripts\start_dev.ps1`；
2. 打开 `http://127.0.0.1:5173/`；
3. 点击“示例”；
4. 选择默认 Schema 和 Template；
5. 点击“导入”；
6. 点击“创建 Task”；
7. 点击“执行”；
8. 查看 Mapping、Validation、Chunk 和 Package；
9. 点击“下载 ZIP”；
10. 如有 Review 队列，再逐条判断是否通过或拒绝。

## 常见问题

### 1. 打开网页是 404

请确认你打开的是：

```text
http://127.0.0.1:5173/
```

不要打开：

```text
http://127.0.0.1:8000/
```

`8000` 是后端 API 地址，根路径显示 404 是正常的。后端健康检查地址是：

```text
http://127.0.0.1:8000/health
```

### 2. 点击导入失败

常见原因：

- JSON 格式错误；
- 粘贴的不是 UIR；
- 缺少 `doc_id`、`uir_version`、`blocks` 等字段；
- 文本框里有多余内容。

建议先点击“示例”跑通流程，再替换成自己的 UIR。

### 3. 创建 Task 按钮不能点

请确认：

- 已经点击“导入”并成功；
- 已选择 Schema；
- 已选择 Template。

### 4. 执行后出现很多 Review

这是正常情况。Review 表示系统不确定，不会强行自动接受。

如果希望减少 Review，需要后续补充更安全的 Template、Regex、Candidate Extraction 或 Knowledge Pack。

### 5. Package 能下载，但 Validation 还有问题

这也是可能的。

Package verification 主要证明结果包结构完整、文件可解析、hash 正确；Validation 检查字段是否符合 Schema。两者不是一回事。

### 6. 后端或前端窗口能不能关

使用过程中不要关闭。

停止系统时再关闭两个窗口：

- backend API 窗口；
- frontend workbench 窗口。

## 新手小结

你可以把整个网页处理流程记成一句话：

```text
启动网页 -> 放入 UIR -> 选择 Schema/Template -> 导入 -> 创建 Task -> 执行 -> 看报告 -> 下载 ZIP
```

如果遇到不确定的 Mapping，就进入 Review；如果结果包生成成功，就可以下载 ZIP 交给下游使用。
## External UIR Adapter Panel

Use this panel when the input is upstream External UIR JSON rather than a
SchemaPack standard UIRDocument. It is not a PDF, Word, Excel, image, or OCR
upload path.

Recommended manual flow:

1. Paste or upload the External UIR JSON.
2. Keep `Route Schema` enabled and leave `DeepSeek` off unless the backend has
   been configured locally.
3. Click `Convert & Preview`.
4. Review the standard UIR preview, adapter summary, warnings, route
   recommendation, and adapter report JSON.
5. Click `Import Standard UIR`.
6. Confirm the recommended schema/template in the main controls.
7. Click `Create Task` in the External UIR panel or use the existing task flow.
8. Execute the task through the existing `Execute` button.

## Schema Draft Lab

Use `Schema Draft Lab` when existing catalogs do not fit a reviewed set of
standard or External UIR samples:

1. Select representative samples and run field discovery.
2. Generate a schema/template draft.
3. Review required fields, aliases, types, risk flags, and validation output.
4. Export only after validation.
5. Submit the exported draft to the normal catalog review process.

Draft generation never activates a schema or template.

## Review Workbench

Use `Review Workbench` for grouped review, impact preview, and controlled batch
decisions:

1. Filter or group pending reviews.
2. Open impact preview before accepting a mapping.
3. Use batch actions only when all selected items satisfy the safety checks.
4. Record rejected mappings as negative knowledge where appropriate.
5. Inspect Knowledge Pack conflict, diff, impact, and rollback information
   before activation.

## Evaluation Center

`Evaluation Center` shows registered datasets, runs, metrics, scorecards, and
report artifacts. A green package result does not imply every target field is
semantically strict-valid; compare package verification, mapping recall,
review-required, required-missing, badcase, and LLM auto-accept metrics
separately.

The page has four sections:

1. `Dataset Registry` lists dataset size and evidence paths.
2. `Evaluation Runs` shows status, package rate, safety counts, and report links.
3. `Metric Scorecard` labels each card as passed, needs attention, or failed.
4. `Regression Gates` shows the current value, operator, threshold, and
   reproduction command.

The fixed warning explains that package verification proves structure,
parseability, hashes, and traceability—not strict field semantics. LLM
suggestions and Schema Drafts never activate production rules automatically.
