# SchemaPack Agent 字段映射指标提升与防过拟合执行文档

目标课题：课题 5「数据格式标准化转换智能体」  
交付对象：Codex / 开发推进人员  
文档目标：在不牺牲安全性、可追溯性和泛化能力的前提下，将字段映射指标稳定提升到任务书建议的 `0.85`，并补齐防过拟合评测制度。

---

## 1. 当前背景与问题判断

### 1.1 项目当前状态

当前项目已经实现课题 5 的主体链路：

```text
UIR / External UIR JSON
-> Adapter / Schema Router
-> Schema/Template Snapshot
-> Candidate Extraction
-> Mapping + Review / Knowledge
-> Transform + Canonical
-> Render + Content Organization
-> Validate
-> Manifest + ZIP
-> Verify + Consumer Contract
```

项目已经具备：

- Schema 驱动转换；
- 字段候选抽取；
- 确定性 mapping；
- review-required 机制；
- JSON / JSONL / Markdown / reports 双形态成果包；
- content organization；
- package manifest、checksum 与 verifier；
- downstream contract；
- Evaluation Center；
- Lineage；
- DeepSeek / LLM suggestion 的安全受控路径。

但字段映射指标尚未稳定达到任务书建议值 `0.85`。

### 1.2 当前可见指标

现有报告中出现过不同口径的指标：

- Real-world corpus：overall recall 约 `0.683`；
- Non-procurement semantic sprint：历史 README 中出现过 `0.8063730159`；
- `phase_d_non_procurement_mapping_eval_report.md` 中 average recall 为 `0.743`；
- `phase_d_semantic_mapping_quality_report.md` 中 average recall 为 `0.7426031746031747`；
- `policy_doc` 是当前主要短板，recall 约 `0.666`；
- `general_doc` 约 `0.824`；
- `meeting_doc` 约 `0.764`；
- 当前 badcase violations 为 `0`，这是必须保持的安全优势。

因此，在继续提升前，必须先统一指标口径。

### 1.3 当前过拟合风险

当前存在过拟合风险，原因包括：

1. **样本量偏小**  
   目前 real-world corpus 约 60 个 UIR，non-procurement 约 50 个样本，容易出现针对当前样例调规则的问题。

2. **缺少独立 blind / shadow gold corpus**  
   当前仓库文档已经说明不能宣称 production shadow / blind gold corpus 上达到 `0.85`。

3. **指标中包含 review-required correct**  
   当前脚本中 mapping recall 的计算逻辑是：

   ```text
   mapping_recall = (auto_accepted_correct + review_required_correct) / gold_signal_count
   ```

   这意味着“自动映射正确”和“进入人工复核但候选正确”都会被计入 recall。课程项目可以接受这种 assisted mapping recall，但如果不单独报告 auto accepted 能力，容易被质疑通过大量转人工刷指标。

4. **如果直接修当前失败样例，容易写成 doc_id 特例**  
   例如针对 `real_policy_011_battery_recycling_rules` 单独写规则，会提高当前报告，但泛化性很弱。

---

## 2. 总体目标

### 2.1 指标目标

最终建议达成以下指标：

```text
assisted_mapping_recall >= 0.85
badcase_violations = 0
required_missing = 0 或接近 0
package_verification_pass_rate = 100%
review_required_count 不明显暴涨
auto_mapping_recall 单独报告
blind/test 指标与 dev 指标差距可解释
```

其中：

- `assisted_mapping_recall`：自动 accepted 正确 + review-required 候选正确；
- `auto_mapping_recall`：只统计自动 accepted 正确；
- `review_required_rate`：进入人工复核的比例；
- `badcase_violations`：错误自动映射的安全违规数量，必须为 0；
- `required_missing`：必填字段缺失数量，目标是降到 0；
- `package_verification_pass_rate`：成果包验证通过率，应保持 100%。

### 2.2 工程目标

实现以下工程能力：

1. 统一当前指标口径；
2. 新增 dev / test / blind 分层评测机制；
3. 新增防过拟合报告；
4. 优先提升 `policy_doc` 字段映射；
5. 增强 gap analysis；
6. 保持 badcase 安全约束；
7. 将指标提升过程沉淀为可复现脚本和报告。

### 2.3 不允许采用的捷径

严禁以下做法：

- 不允许根据 `doc_id` 写特例规则；
- 不允许在 mapping 规则里读取 gold label；
- 不允许为了 recall 自动接受高风险 mapping；
- 不允许把所有疑难字段都转 review 来虚高 recall；
- 不允许修改评分脚本使指标“变好看”但实际能力没有提升；
- 不允许牺牲 badcase filters；
- 不允许将 LLM suggestion 自动写入生产规则或自动 accepted。

---

## 3. 推荐分支与工作方式

### 3.1 建议分支

```text
feature/mapping-recall-085-guarded
```

### 3.2 提交策略

建议按阶段小步提交：

1. `chore(eval): normalize mapping evaluation reports`
2. `feat(eval): add split-based mapping evaluator`
3. `feat(eval): add overfitting risk report`
4. `feat(mapping): strengthen policy document field candidates`
5. `feat(mapping): add guarded negative badcases`
6. `test(eval): add regression gates for mapping recall and badcase safety`
7. `docs: add mapping recall 0.85 improvement report`

### 3.3 每次提交前必须运行

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

如果本地没有完整环境，至少运行和本次变更相关的 pytest、ruff 和对应 evaluator。

---

## 4. 第一阶段：统一当前指标口径

### 4.1 目标

确认当前主分支可复现的最新基线到底是多少，避免 README、Phase D 报告和其他报告口径不一致。

### 4.2 需要检查的文件

重点检查：

```text
README.md
reports/phase_d_non_procurement_mapping_eval_report.md
reports/phase_d_semantic_mapping_quality_report.md
reports/non_procurement_mapping_eval_report.md
reports/real_world_mapping_eval_report.json
reports/real_world_mapping_eval_report.md
scripts/eval_non_procurement_mapping.py
scripts/eval_non_procurement_doc.py
scripts/eval_real_world_mapping.py
scripts/eval_support.py
```

### 4.3 需要运行的命令

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\non_procurement_mapping_eval_report.json `
  --markdown reports\non_procurement_mapping_eval_report.md
```

如果 real-world evaluator 需要服务运行，先启动后端：

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

然后在仓库根目录运行 evaluator。

### 4.4 输出要求

新增或更新一个报告：

```text
reports/mapping_metric_baseline_snapshot.md
```

报告至少包含：

```markdown
# Mapping Metric Baseline Snapshot

## Reproducible Command
...

## Current Metrics
- dataset_size:
- average_recall:
- auto_mapping_recall:
- assisted_mapping_recall:
- review_required_count:
- required_missing_count:
- badcase_violations:
- package_verification_pass:

## Metric Definition
...

## Known Inconsistencies
...

## Decision
Use this report as the baseline for the 0.85 improvement sprint.
```

### 4.5 验收标准

- 能明确说出当前基线是哪个报告、哪个命令生成的；
- README 中历史指标和当前指标不再混用；
- 后续所有提升都以这个 baseline 为准；
- 如果历史报告保留，必须标注“historical”。

---

## 5. 第二阶段：拆分指标，避免 review 刷分

### 5.1 目标

在现有 `mapping_recall` 基础上新增更透明的指标：

```text
auto_mapping_recall
assisted_mapping_recall
review_required_rate
missing_gold_mapping_rate
badcase_violation_count
```

### 5.2 当前评分逻辑

当前 `scripts/eval_support.py` 中 `score_mapping_report` 的核心逻辑是：

```python
mapping_recall = safe_ratio(
    accepted_correct + review_correct,
    gold_signal_count
)
```

这应保留为 `assisted_mapping_recall`，同时新增 `auto_mapping_recall`。

### 5.3 建议修改

在 `scripts/eval_support.py` 的 `score_mapping_report` 返回值中新增：

```python
"auto_mapping_recall": safe_ratio(accepted_correct, gold_signal_count),
"assisted_mapping_recall": safe_ratio(accepted_correct + review_correct, gold_signal_count),
"review_required_recall": safe_ratio(review_correct, gold_signal_count),
"review_required_rate": safe_ratio(len(review_items), max(len(accepted) + len(review_items), 1)),
```

同时保留旧字段：

```python
"mapping_recall": safe_ratio(accepted_correct + review_correct, gold_signal_count)
```

为了兼容历史报告，`mapping_recall` 可继续作为 assisted recall，但报告中必须解释清楚。

### 5.4 聚合函数修改

在 `aggregate_mapping_metrics` 中加入聚合：

```python
accepted_correct_total
review_correct_total
gold_signal_total
review_item_total
accepted_item_total
```

输出：

```python
"auto_mapping_recall": safe_ratio(auto_accepted_correct, denominator),
"assisted_mapping_recall": safe_ratio(auto_accepted_correct + review_required_correct, denominator),
"review_required_recall": safe_ratio(review_required_correct, denominator),
"review_required_rate": safe_ratio(review_item_total, accepted_item_total + review_item_total),
```

### 5.5 Markdown 报告修改

所有 mapping evaluator 的 Markdown summary 中应显示：

```markdown
- Auto mapping recall:
- Assisted mapping recall:
- Review-required recall:
- Review-required rate:
- Required missing:
- Badcase violations:
- Package verification pass:
```

### 5.6 验收标准

- 报告不再只显示一个模糊的 average recall；
- 可以区分“自动映射能力”和“人工辅助候选能力”；
- 如果 assisted recall 达到 0.85，但 auto recall 偏低，也能诚实说明。

---

## 6. 第三阶段：新增 dev / test / blind 分层评测

### 6.1 目标

建立防过拟合评测制度，避免只针对当前 50/60 个样例调规则。

### 6.2 数据划分原则

必须按文档维度划分，不能按字段划分。

推荐：

| Split | 用途 | 是否允许看错误明细 | 是否允许调规则 |
| --- | --- | --- | --- |
| dev | 规则开发、错误分析 | 允许 | 允许 |
| test | 回归验证 | 允许看汇总，谨慎看明细 | 不针对单个样例修 |
| blind | 最终验收 | 只看最终指标 | 不允许 |

### 6.3 推荐目录结构

```text
examples/real_world/splits/
  mapping_split_manifest.json
  dev_doc_ids.txt
  test_doc_ids.txt
  blind_doc_ids.txt

examples/real_world/gold/
  mapping_gold.jsonl
  mapping_gold_dev.jsonl
  mapping_gold_test.jsonl
  mapping_gold_blind.jsonl
```

如果 blind gold 不适合公开，可将 blind gold 放在本地或私有路径，但需要保留 blind dataset manifest。

### 6.4 Split manifest 示例

```json
{
  "version": "1.0.0",
  "created_for": "mapping_recall_085_guarded_sprint",
  "split_policy": "document_level_split_no_doc_id_specific_rules",
  "random_seed": 20260708,
  "dev": {
    "doc_count": 50,
    "source": "existing_non_procurement_and_real_world_gold"
  },
  "test": {
    "doc_count": 30,
    "source": "new_or_held_out_real_world_uir"
  },
  "blind": {
    "doc_count": 30,
    "source": "new_unseen_real_world_uir",
    "gold_visibility": "final_evaluation_only"
  },
  "leakage_rules": [
    "same doc_id cannot appear in multiple splits",
    "same source_path cannot appear in multiple splits",
    "rules must not branch on doc_id",
    "gold labels must not be read by runtime mapping code"
  ]
}
```

### 6.5 新增脚本建议

新增：

```text
scripts/eval_mapping_splits.py
```

功能：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_mapping_splits.py `
  --splits examples\real_world\splits\mapping_split_manifest.json `
  --out-dir reports\mapping_splits
```

输出：

```text
reports/mapping_splits/dev_mapping_eval_report.json
reports/mapping_splits/dev_mapping_eval_report.md
reports/mapping_splits/test_mapping_eval_report.json
reports/mapping_splits/test_mapping_eval_report.md
reports/mapping_splits/blind_mapping_eval_report.json
reports/mapping_splits/blind_mapping_eval_report.md
reports/mapping_splits/summary.md
```

### 6.6 Split summary 内容

`reports/mapping_splits/summary.md` 至少包含：

```markdown
# Mapping Split Evaluation Summary

| Split | Docs | Auto Recall | Assisted Recall | Review Rate | Required Missing | Badcase Violations | Package Pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | | | | | | | |
| test | | | | | | | |
| blind | | | | | | | |

## Generalization Gap
- dev vs test assisted recall gap:
- test vs blind assisted recall gap:
- conclusion:
```

### 6.7 过拟合判定阈值

建议暂定：

```text
dev_assisted_recall - test_assisted_recall <= 0.05
test_assisted_recall - blind_assisted_recall <= 0.05
badcase_violations = 0 for all splits
required_missing_count does not increase on test/blind
```

如果 dev 达到 0.90，但 blind 只有 0.70，应判定为过拟合，不可宣称达标。

### 6.8 验收标准

- 有明确 split manifest；
- 同一 doc_id 不跨 split；
- evaluator 可以分别跑 dev / test / blind；
- 报告能体现 generalization gap；
- 指标提升不只发生在 dev 上。

---

## 7. 第四阶段：生成 Gap Analysis，按收益排序修复

### 7.1 目标

不要凭感觉调规则，要先生成按文档类型、字段、失败原因排序的 gap report。

### 7.2 新增报告

建议新增：

```text
scripts/analyze_mapping_gaps.py
reports/mapping_gap_analysis.md
reports/mapping_gap_analysis.json
```

### 7.3 Gap 维度

至少统计：

1. by doc_type；
2. by field；
3. by missing required field；
4. by review-required reason；
5. by failure reason；
6. by source evidence pattern；
7. by accepted / review / unmapped；
8. by high-risk blocked mapping；
9. by estimated gain。

### 7.4 Estimated gain 计算建议

每个字段的优先级可以按下面方式估算：

```text
estimated_gain = missing_count * required_weight + low_recall_count * recall_weight - badcase_risk_penalty
```

建议权重：

```text
required_weight = 3
recall_weight = 1
badcase_risk_penalty = 2 或更高
```

### 7.5 当前已知高优先级

当前最优先修复：

1. `policy_doc.issuer`
2. `policy_doc.publish_date`
3. `policy_doc.effective_date`
4. `policy_doc.document_number`
5. `policy_doc.policy_measures`
6. `policy_doc.application_conditions`
7. `policy_doc.application_materials`
8. `general_doc.title`
9. `general_doc.deadline`
10. `meeting_doc.decisions` / `action_items`

### 7.6 输出示例

```markdown
# Mapping Gap Analysis

## Ranked Improvement Candidates

| Rank | Doc Type | Field | Current Problem | Evidence | Estimated Gain | Risk |
| ---: | --- | --- | --- | --- | ---: | --- |
| 1 | policy_doc | issuer | required missing / weak evidence | 发文机关、发布单位等别名未覆盖 | high | medium |
| 2 | policy_doc | publish_date | missing / confused with effective_date | 发布日期、印发日期、成文日期 | high | high |
| 3 | policy_doc | effective_date | confused with publish_date | 自...起施行 | medium | high |
```

### 7.7 验收标准

- 每一轮 mapping 优化前都有 gap report；
- 每个新增规则都能对应到一个 gap 类型；
- 不针对单个 doc_id 修规则；
- 新规则必须有正样本和负样本。

---

## 8. 第五阶段：优先增强 policy_doc 字段映射

### 8.1 目标

将 `policy_doc` 从当前约 `0.666` 提升到至少 `0.80+`，这是全局平均达到 `0.85` 的关键。

### 8.2 规则设计原则

必须采用“字段通用模式”，禁止 doc_id 特例。

允许：

```text
如果元数据块或正文前 20 个 block 中出现 发文机关/发布单位/印发机关/制定机关，则作为 issuer 候选。
```

禁止：

```text
如果 doc_id == real_policy_005_ai_industry_guide，则 issuer = xxx。
```

### 8.3 issuer 增强

#### 8.3.1 正向证据关键词

```text
发文机关
发布单位
发布机构
制定机关
印发机关
主管部门
牵头单位
责任单位
联合发布
来源：
```

#### 8.3.2 机构实体模式

```text
.*人民政府
.*办公厅
.*办公室
.*委员会
.*发展改革委
.*工业和信息化部
.*财政部
.*教育部
.*商务部
.*市场监督管理局
.*税务局
.*海关总署
.*民航局
.*厅
.*局
.*委
.*部
```

#### 8.3.3 issuer 候选优先级

建议优先级：

```text
explicit_label_issuer > header_issuing_authority > official_org_near_title > source_org > weak_org_mention
```

其中：

- explicit_label_issuer：有明确“发文机关/发布单位”标签；
- header_issuing_authority：标题附近出现官方机构；
- official_org_near_title：正文前部机构名称；
- source_org：来源字段，仅作为低置信候选，通常进入 review；
- weak_org_mention：正文中普通机构提及，不可自动 accepted。

#### 8.3.4 issuer 负样本

不得自动映射：

```text
联系人 -> issuer
联系电话 -> issuer
来源网站 -> issuer
承办单位 -> issuer，除非 schema 明确要求
服务窗口 -> issuer
地址 -> issuer
```

### 8.4 publish_date 增强

#### 8.4.1 正向证据关键词

```text
发布日期
发布时间
公布日期
印发日期
成文日期
发文日期
签发日期
```

#### 8.4.2 日期模式

```text
YYYY-MM-DD
YYYY/MM/DD
YYYY年M月D日
YYYY 年 M 月 D 日
二〇二四年六月一日
2024.06.01
```

#### 8.4.3 publish_date 优先级

```text
发布日期 > 公布日期 > 印发日期 > 成文日期 > 发文日期 > header date
```

#### 8.4.4 publish_date 负样本

不得自动映射：

```text
施行日期 -> publish_date
实施日期 -> publish_date
有效期至 -> publish_date
截止日期 -> publish_date
申报截止时间 -> publish_date
检索日期 -> publish_date
retrieved_at -> publish_date
```

### 8.5 effective_date 增强

#### 8.5.1 正向证据关键词

```text
施行日期
实施日期
生效日期
自...起施行
自...起实施
本办法自...起施行
有效期自...至...
```

#### 8.5.2 负样本

不得自动映射：

```text
发布日期 -> effective_date
印发日期 -> effective_date
成文日期 -> effective_date
检索日期 -> effective_date
```

### 8.6 document_number 增强

#### 8.6.1 常见模式

```text
〔2024〕12号
[2024] 12号
2024年第12号
第12号
公告2024年第12号
通知编号：XXX
文号：XXX
```

#### 8.6.2 负样本

不得将以下内容映射为文号：

```text
电话
邮编
统一社会信用代码
身份证号
表格序号
项目编号，除非 schema 要的是 project_id
```

### 8.7 policy_measures 增强

#### 8.7.1 标题关键词

```text
政策措施
支持措施
主要措施
重点任务
工作措施
保障措施
扶持政策
支持内容
奖励标准
补贴标准
```

#### 8.7.2 提取范围

优先提取标题下的 section，而不是单个短字段。

### 8.8 application_conditions 增强

#### 8.8.1 标题关键词

```text
申报条件
申请条件
适用条件
支持条件
认定条件
办理条件
准入条件
```

### 8.9 application_materials 增强

#### 8.9.1 标题关键词

```text
申报材料
申请材料
提交材料
所需材料
材料清单
附件材料
证明材料
```

### 8.10 target_audience / service_object 增强

#### 8.10.1 关键词

```text
支持对象
服务对象
适用对象
面向对象
申报主体
企业范围
申请人
受理对象
```

### 8.11 实现位置建议

Codex 需要先搜索当前 mapping 规则位置。建议搜索关键词：

```text
policy_doc_base_v1
issuer
publish_date
effective_date
document_number
alias
mapping rule
candidate extraction
badcase filter
```

可能涉及：

```text
backend/app/...
backend/app/services/...
backend/app/catalogs/...
backend/app/mapping/...
configs/...
schemas/...
templates/...
examples/...
```

实际以仓库结构为准。

### 8.12 验收标准

- `policy_doc` recall 明显提升；
- `issuer`、`publish_date` required missing 降到 0；
- `effective_date` 与 `publish_date` 不互相误映射；
- badcase violations 仍为 0；
- review-required 不明显暴涨。

---

## 9. 第六阶段：补充 general_doc 与 meeting_doc

### 9.1 general_doc 当前目标

`general_doc` 当前 recall 已接近 `0.824`，应补少量长尾字段，使其稳定超过 `0.85`。

### 9.2 general_doc 优先字段

```text
title
category
deadline
contact
summary
source
```

### 9.3 general_doc 规则建议

#### title

- 优先使用一级标题、文档标题、metadata title；
- 避免把来源网站、导航标题、栏目名当 title。

#### deadline

正向关键词：

```text
截止日期
截止时间
申报截止
报名截止
提交截止
办理期限
受理时间
```

负样本：

```text
发布日期
更新时间
检索日期
```

#### contact

正向关键词：

```text
联系人
联系电话
咨询电话
联系方式
邮箱
```

负样本：

```text
发布单位
主管部门
```

### 9.4 meeting_doc 当前目标

`meeting_doc` 当前 recall 约 `0.764`，strict pass 较好，但仍可提升内容型字段。

### 9.5 meeting_doc 优先字段

```text
meeting_title
meeting_date
meeting_location
attendees
chairperson
decisions
action_items
topics
```

### 9.6 meeting_doc 规则建议

#### attendees

关键词：

```text
参会人员
出席人员
列席人员
与会人员
参会单位
```

#### chairperson

关键词：

```text
主持人
会议由...主持
```

#### decisions

关键词：

```text
会议决定
会议要求
审议通过
形成如下决议
决定如下
```

#### action_items

关键词：

```text
下一步工作
责任分工
工作安排
任务清单
由...负责
完成时限
```

### 9.7 验收标准

- `general_doc` assisted recall >= 0.85；
- `meeting_doc` assisted recall >= 0.85 或至少明显提升；
- 内容型字段进入 review 可接受，但要有 evidence；
- 不引入 high-risk auto accepted。

---

## 10. 第七阶段：增强 badcase 负样本与安全门禁

### 10.1 目标

提升 recall 的同时保持：

```text
badcase_violations = 0
llm_auto_accepted_count = 0
high_risk_auto_accepted = 0
```

### 10.2 新增负样本类型

建议添加 known_badcases：

```text
retrieved_at -> publish_date
retrieved_at -> effective_date
发布日期 -> effective_date
印发日期 -> effective_date
施行日期 -> publish_date
实施日期 -> publish_date
有效期至 -> publish_date
来源网站 -> issuer
联系人 -> issuer
联系电话 -> issuer
会议地点 -> issuer
会议日期 -> publish_date
项目编号 -> document_number，除非 schema 明确匹配
```

### 10.3 报告要求

每次 mapping eval 输出：

```markdown
## Badcase Safety
- badcase violations:
- high-risk auto accepted:
- LLM auto accepted:
- new negative cases covered:
```

### 10.4 验收标准

- 新增负样本后，badcase violations 仍为 0；
- recall 提升不是通过危险自动接受实现的；
- 如果某字段证据不足，应进入 review-required，而不是自动 accepted。

---

## 11. 第八阶段：新增防过拟合扫描

### 11.1 目标

自动检查代码和配置中是否出现明显过拟合信号。

### 11.2 新增脚本

建议新增：

```text
scripts/check_mapping_overfit_risk.py
reports/mapping_overfit_risk_report.md
reports/mapping_overfit_risk_report.json
```

### 11.3 检查项

#### 11.3.1 doc_id 特例扫描

扫描 mapping 相关代码、catalog、template、config 中是否出现：

```text
real_policy_
real_general_
real_meeting_
real_procurement_
doc_id ==
source_path == examples/real_world/uir/
```

如果这些内容出现在 gold、reports、examples 中可以接受；如果出现在 runtime mapping 代码中，应标记为 high risk。

#### 11.3.2 gold 泄漏扫描

runtime 代码中不应读取：

```text
mapping_gold.jsonl
mapping_gold_dev.jsonl
mapping_gold_test.jsonl
mapping_gold_blind.jsonl
known_badcases
expected_mappings
expected_review_required
```

评分脚本可以读取，runtime mapping 代码不可以。

#### 11.3.3 过窄 alias 扫描

如果 alias 规则只针对单个样本文本中的极长标题或唯一短语，应标记为 medium risk。

#### 11.3.4 review 刷分风险

如果 review_required_count 大幅增加，但 auto_mapping_recall 不提升，应标记为 risk。

建议阈值：

```text
review_required_rate increase > 0.10 and auto_mapping_recall increase < 0.02
```

### 11.4 报告示例

```markdown
# Mapping Overfit Risk Report

## Summary
- risk_level: low / medium / high
- doc_id_specific_rules_found:
- gold_leakage_found:
- review_inflation_risk:
- dev_test_gap:

## Findings
...

## Decision
Pass / Fail
```

### 11.5 验收标准

- 每次最终评测前运行 overfit risk check；
- high risk 必须修复；
- medium risk 必须解释；
- 报告纳入最终交付文档。

---

## 12. 第九阶段：回归门禁与 CI 化

### 12.1 目标

将指标提升固化为 regression gate，防止后续改动导致退化。

### 12.2 新增门禁建议

新增或更新 regression gate：

```text
scripts/check_mapping_quality_gate.py
```

建议支持参数：

```powershell
backend\.venv\Scripts\python.exe scripts\check_mapping_quality_gate.py `
  --report reports\mapping_splits\summary.json `
  --min-assisted-recall 0.85 `
  --max-badcase-violations 0 `
  --max-required-missing 0 `
  --max-dev-test-gap 0.05 `
  --max-test-blind-gap 0.05
```

### 12.3 分阶段门禁

#### Sprint 中期

```text
non_procurement assisted recall >= 0.80
policy_doc assisted recall >= 0.75
badcase violations = 0
```

#### Sprint 后期

```text
non_procurement assisted recall >= 0.85
policy_doc assisted recall >= 0.80
test/blind assisted recall 接近 dev
badcase violations = 0
```

#### 最终验收

```text
assisted recall >= 0.85
badcase violations = 0
required missing = 0 或有合理说明
package verification = 100%
overfit risk report = pass
```

### 12.4 验收标准

- 不满足门禁时脚本返回非 0；
- 报告能指出失败原因；
- CI 或 `verify_all.py` 可选择性集成该门禁。

---

## 13. 第十阶段：最终报告与答辩材料

### 13.1 新增最终报告

建议新增：

```text
reports/mapping_recall_085_improvement_report.md
```

### 13.2 报告结构

```markdown
# Mapping Recall 0.85 Improvement Report

## 1. Goal
说明课题 5 字段映射指标要求，以及本轮目标。

## 2. Baseline
列出优化前指标。

## 3. Method
说明不是 doc_id 特例，而是基于字段语义、标签、上下文和负样本的通用规则增强。

## 4. Metric Definition
区分 auto_mapping_recall 和 assisted_mapping_recall。

## 5. Dataset Split
说明 dev / test / blind 划分，避免过拟合。

## 6. Improvements
按字段列出新增规则和安全约束。

## 7. Results
列出 dev/test/blind 指标。

## 8. Safety
说明 badcase violations = 0、LLM auto accepted = 0、high-risk auto accepted = 0。

## 9. Overfitting Risk Control
说明 doc_id 扫描、gold leakage 扫描、generalization gap。

## 10. Remaining Limitations
诚实说明仍有少量 review-required 或长尾字段。

## 11. Commands
列出所有可复现命令。
```

### 13.3 答辩推荐表述

```text
本轮优化没有针对单个 doc_id 编写特例，而是基于字段语义、标题结构、标签证据、日期模式和负样本约束增强通用映射能力。我们将评测拆分为 dev/test/blind，分别报告 auto mapping recall、assisted mapping recall、review-required rate 和 badcase violations。最终在保持 badcase violations 为 0、package verification 为 100% 的前提下，将 assisted mapping recall 提升到 0.85 左右，并通过 overfit risk report 证明没有明显 gold 泄漏或样本特例化。
```

---

## 14. 建议开发任务清单

### Task 1：统一指标口径

- [ ] 重新运行现有 evaluator；
- [ ] 生成 `mapping_metric_baseline_snapshot.md`；
- [ ] README 中将历史指标和当前指标分开；
- [ ] 确认后续 baseline。

### Task 2：拆分 recall 指标

- [ ] 修改 `score_mapping_report`；
- [ ] 新增 `auto_mapping_recall`；
- [ ] 新增 `assisted_mapping_recall`；
- [ ] 新增 `review_required_rate`；
- [ ] 更新 Markdown 报告。

### Task 3：增加 split evaluator

- [ ] 新增 split manifest；
- [ ] 新增 `eval_mapping_splits.py`；
- [ ] 输出 dev/test/blind 报告；
- [ ] 输出 summary 与 generalization gap。

### Task 4：增加 gap analysis

- [ ] 新增 `analyze_mapping_gaps.py`；
- [ ] 按 doc_type / field / reason 排序；
- [ ] 输出 estimated gain；
- [ ] 确认 policy_doc 为第一优先级。

### Task 5：增强 policy_doc 映射

- [ ] 增强 issuer；
- [ ] 增强 publish_date；
- [ ] 增强 effective_date；
- [ ] 增强 document_number；
- [ ] 增强 policy_measures；
- [ ] 增强 application_conditions；
- [ ] 增强 application_materials；
- [ ] 增强 target_audience / service_object。

### Task 6：增强 general_doc / meeting_doc

- [ ] 修 general_doc title / deadline / contact；
- [ ] 修 meeting_doc attendees / chairperson / decisions / action_items；
- [ ] 保持内容型字段证据链。

### Task 7：增加 badcase 负样本

- [ ] 增加日期混淆负样本；
- [ ] 增加 issuer 混淆负样本；
- [ ] 增加 document_number 混淆负样本；
- [ ] 确保 badcase violations = 0。

### Task 8：增加过拟合风险扫描

- [ ] 新增 `check_mapping_overfit_risk.py`；
- [ ] 扫描 doc_id 特例；
- [ ] 扫描 gold 泄漏；
- [ ] 扫描 review inflation；
- [ ] 输出 overfit risk report。

### Task 9：增加质量门禁

- [ ] 新增或更新 `check_mapping_quality_gate.py`；
- [ ] 支持 assisted recall 阈值；
- [ ] 支持 badcase 阈值；
- [ ] 支持 dev/test/blind gap 阈值。

### Task 10：最终文档

- [ ] 生成 `mapping_recall_085_improvement_report.md`；
- [ ] 更新 `docs/交接/requirement_mapping.md`；
- [ ] 更新 README 当前结论；
- [ ] 补充答辩口径。

---

## 15. 最终验收清单

完成后应满足：

```text
[ ] 当前基线指标口径已统一
[ ] auto_mapping_recall 与 assisted_mapping_recall 已分开报告
[ ] dev/test/blind split 已建立
[ ] overfit risk report 已生成并通过
[ ] policy_doc recall 明显提升
[ ] issuer required missing = 0
[ ] publish_date required missing = 0
[ ] badcase violations = 0
[ ] llm_auto_accepted_count = 0
[ ] package verification = 100%
[ ] review_required_count 没有异常暴涨
[ ] split generalization gap 可接受
[ ] 最终 assisted_mapping_recall >= 0.85
[ ] 所有脚本和报告可复现
```

---

## 16. 给 Codex 的直接执行提示词

可以直接把下面这段交给 Codex：

```text
创建分支 feature/mapping-recall-085-guarded，按本文档推进字段映射指标提升任务。目标是在不引入 doc_id 特例、不读取 gold label、不破坏 badcase safety、不自动接受 LLM suggestion 的前提下，将字段映射 assisted mapping recall 提升到 0.85，并新增 auto_mapping_recall、assisted_mapping_recall、review_required_rate、dev/test/blind split evaluator、gap analysis、overfit risk check 和 quality gate。优先修复 policy_doc 的 issuer、publish_date、effective_date、document_number、policy_measures、application_conditions、application_materials 等字段。每轮修改后运行 evaluator、badcase 检查和 package verifier，输出可复现报告。最终更新 README、docs/交接/requirement_mapping.md 和 reports/mapping_recall_085_improvement_report.md。
```

---

## 17. 风险提示

即使最终当前数据集达到 `0.85`，也不要直接宣称“生产场景已达 0.85”。更稳妥的表述是：

```text
在课程规模的冻结测试集与新增盲测集上，字段映射 assisted recall 达到或接近 0.85；同时保持 badcase violations 为 0、package verification 为 100%，并通过过拟合风险扫描。后续若接入真实企业生产数据，需要继续扩展 blind corpus 和人工标注集。
```
