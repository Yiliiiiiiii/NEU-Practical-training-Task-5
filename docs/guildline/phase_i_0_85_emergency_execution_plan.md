# Phase I：0.85+ 目标字段自动映射准确率冲刺执行文档

> 交付对象：Codex / 工程实现智能体  
> 目标：在不牺牲 badcase 安全、可追溯、人审治理与报告真实性的前提下，将 **目标字段自动映射准确率 / average mapping recall 稳定提升到 0.85+**。  
> 当前状态依据：Phase H 执行报告、Phase H gap drilldown、Phase H acceptance、Phase H review subagent、DeepSeek review loop、production shadow blocker。  
> 重要原则：本计划不是“再生成报告”，而是要求 Codex 实际修改候选抽取、证据排序、Review/Knowledge 激活闭环和评测数据闭环，使指标真实生效。

---

## 0. 当前结论与本轮目标

### 0.1 当前 Phase H 结论

Phase H 已完成报告治理、安全审查框架和生产 blind 阻断说明，但核心质量指标没有提升：

| 指标 | Phase H 当前值 | 说明 |
|---|---:|---|
| non_procurement_average_recall | `0.7426031746031747` | 与 Phase G 相同，delta = 0 |
| semantic_quality_average_recall | `0.7184920634920635` | 与 Phase G 相同，delta = 0 |
| strict_pass | `39/50` | 与 Phase G 相同，delta = 0 |
| package_verification | `50/50` | 结构出包稳定，但不代表语义正确 |
| badcase_violations | `0` | 安全边界保持 |
| llm_auto_accepted_count | `0` | LLM 未绕过人审 |
| secret_leaks | `0` | 安全审计通过 |
| production blind docs | `0` | blind corpus 为空，不能声明生产 0.85 |
| production gold labels | `0` | gold 为空，不能声明生产 0.85 |

Phase H Mapping Gap Drilldown 显示：

```text
Dataset size = 50
Gap count = 110
```

Top gaps 仍集中在：

```text
policy_doc.publish_date: candidate_not_extracted x15
meeting_doc.meeting_number: candidate_not_extracted x7 / 明细中覆盖 15 个 meeting docs
meeting_doc.topics: candidate_not_extracted x7
policy_doc.policy_measures: candidate_not_extracted x7
general_doc.application_conditions: candidate_extracted_but_not_ranked x6 / 明细中覆盖 15 个 general docs
general_doc.contact: candidate_not_extracted x6
general_doc.service_object: candidate_not_extracted x6
meeting_doc.organizer: candidate_not_extracted x6
policy_doc.target_audience: candidate_not_extracted x6
policy_doc.effective_date: candidate_not_extracted x5
policy_doc.issuer: candidate_not_extracted x5
```

### 0.2 本轮不能接受的结果

以下结果视为执行失败：

1. 只新增 Markdown / JSON 报告，但 recall、strict pass、gap_count 没有实际改善。
2. 只让 DeepSeek smoke passed，但 `deepseek_candidates = 0`、`evidence_linked_candidates = 0`、`measurable_recall_delta = 0`。
3. Review subagent 批准候选，但候选停留在 `draft_only`，未进入 gated active knowledge，未影响 evaluator。
4. 通过降低 badcase、降低 confidence threshold、把 LLM-only suggestion 自动 accepted 来刷指标。
5. 修改评测报告数值而不修改抽取、映射、验证逻辑。
6. 删除 required fields 或弱化 strict validator 来提升 strict pass。
7. 把 package verification 当成 semantic recall 0.85 的替代证明。

### 0.3 本轮核心目标

本轮必须把目标拆成两层。

#### A. Local evaluator 0.85+

在当前 50-sample non-procurement evaluator 上达成：

| 指标 | 最低目标 | 冲刺目标 |
|---|---:|---:|
| non_procurement_average_recall | `>= 0.8500` | `>= 0.8700` |
| semantic_quality_average_recall | `>= 0.8300` | `>= 0.8500` |
| strict_pass | `>= 43/50` | `>= 45/50` |
| required_missing_doc_count | `<= 1` | `0` |
| required_missing_field_count | `<= 2` | `0` |
| review_required_doc_count | `<= 12` | `<= 8` |
| review_required_field_count | `<= 14` | `<= 10` |
| package_verification | `50/50` | `50/50` |
| badcase_violations | `0` | `0` |
| llm_auto_accepted_count | `0` | `0` |
| secret_leaks | `0` | `0` |
| old_snapshot_unchanged | `True` | `True` |

#### B. Production blind 0.85 claim readiness

必须至少把 production shadow 从 `blocked` 推进到 `evaluated`：

| 指标 | 最低目标 |
|---|---:|
| blind docs | `>= 10` |
| gold labels | `> 0`，每个 blind doc 至少覆盖核心 required fields |
| blind badcases | `>= 1` 个 registry，禁止高风险错映射 |
| can_claim_0_85 | 若样本太少，可以仍为 false，但必须说明 “small blind smoke not production claim” |
| production shadow status | 不再是 manifest/gold empty blocker |

若时间不足，允许不声明 production blind 0.85，但不允许继续保持 `blind docs = 0`、`gold labels = 0`。

---

## 1. 执行总原则

### 1.1 不走捷径原则

Codex 必须遵守：

```text
不能关闭 badcase filter。
不能让 LLM suggestion 自动 accepted。
不能让 DeepSeek 直接激活 schema/template/knowledge pack。
不能让 draft knowledge pack 影响当前 task。
不能修改历史 task snapshot。
不能为了 strict pass 删除 required fields。
不能把 source-untraceable mapping 改成 accepted。
不能把 low-confidence fuzzy mapping 改成 accepted。
不能手工改 reports 数值。
```

### 1.2 可以使用的增强手段

允许并鼓励使用以下方法：

1. **确定性候选抽取增强**：regex、heading-aware extraction、section pattern、position-aware metadata、date role classifier。
2. **证据排序增强**：source anchor、heading proximity、field type、date role、negative context、badcase penalty、schema field prior。
3. **Review subagent 模拟人工审查**：只对 source-backed、low-risk、deterministic candidates 做 simulated approval。
4. **DeepSeek 候选建议**：只用于 gap rows，输出候选 + evidence hints，不得自动 accepted。
5. **Review/Knowledge 闭环**：approved candidates -> draft pack -> impact preview -> badcase gate -> active pack -> rerun evaluator。
6. **严格验证修复**：日期标准化、required field source-backed fill、semantic review reason 降低。
7. **生产 blind scaffold 填充**：补 manifest、gold labels、badcase registry、冻结规则。
8. **测试驱动**：每个字段一组 targeted tests，先失败后修复。
9. **报告一致性**：每次指标更新后重新生成一致性报告，不手工改 JSON。

### 1.3 指标提升公式

当前 local non-procurement average recall 为：

```text
0.7426031746031747
```

要达到 0.85，50 个样本的总 recall 需要增加：

```text
(0.85 - 0.7426031746031747) * 50 ≈ 5.3698 个满分文档等价增量
```

不能指望单个 alias 或单个样本完成目标。必须集中消除高频 gap：

```text
policy_doc.publish_date x15
meeting_doc.meeting_number x15 明细级
meeting_doc.topics x7
policy_doc.policy_measures x7
general_doc.application_conditions x15 明细级 ranking gap
general_doc.contact x6
general_doc.service_object x6
meeting_doc.organizer x6
policy_doc.target_audience x6
policy_doc.effective_date x5
policy_doc.issuer x5
```

本轮目标不是修完全部 110 gaps，而是优先修掉 **最容易安全自动化、最高频、最能提升 recall/strict pass 的 60–75 个 gaps**。

---

## 2. 推荐分支与提交策略

### 2.1 分支

```powershell
git status
git checkout -b phase-i-0-85-semantic-mapping
```

### 2.2 提交粒度

建议按以下 commit 顺序提交：

1. `test: add phase i mapping gap regression tests`
2. `feat: enhance policy date and issuer candidate extraction`
3. `feat: enhance meeting metadata and topic extraction`
4. `feat: improve general application condition ranking`
5. `feat: add review subagent gated activation workflow`
6. `feat: add deepseek evidence-linked candidate loop`
7. `feat: add production shadow blind smoke corpus`
8. `test: update evaluators and report consistency gates`
9. `docs: add phase i acceptance and remaining gap reports`

每个 commit 必须能独立通过对应单元测试。最后再跑全量验证。

---

## 3. 第一阶段：冻结基线与定位真实代码入口

### 3.1 运行基线

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
Push-Location frontend
npm.cmd test
Pop-Location
```

### 3.2 重跑当前 evaluator，确认未改动前指标

```powershell
# 启动 backend 后执行
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --timeout 60 `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\phase_i_baseline_non_procurement_mapping_eval_report.json `
  --markdown reports\phase_i_baseline_non_procurement_mapping_eval_report.md

backend\.venv\Scripts\python.exe scripts\eval_semantic_mapping_quality.py `
  --out reports\phase_i_baseline_semantic_mapping_quality_report.json `
  --markdown reports\phase_i_baseline_semantic_mapping_quality_report.md
```

如果脚本名不同，使用 `rg` 查找：

```powershell
rg "semantic_mapping_quality|mapping_gap|non_procurement" scripts backend tests reports -n
```

### 3.3 定位候选抽取、映射排序、validator 代码

Codex 应先定位实际代码，不要臆造文件名。

```powershell
rg "candidate_not_extracted|candidate_extraction|FieldCandidate|field candidate|extract_candidates" backend tests scripts -n
rg "mapping recall|MappingDecision|confidence_tier|review_required_reason|badcase" backend tests scripts -n
rg "publish_date|effective_date|issuer|meeting_number|application_conditions" backend tests scripts examples -n
rg "strict validation|required missing|date_format_invalid" backend tests scripts -n
rg "knowledge pack|effective-template|review_approved|draft_only|activate" backend tests scripts -n
```

输出一个内部 notes 文件：

```text
reports/phase_i_code_entrypoint_notes.md
```

内容包含：

```text
- candidate extraction service path
- mapping/ranking service path
- validator service path
- review service path
- knowledge pack service path
- evaluators involved
- tests currently covering policy/general/meeting
```

---

## 4. 第二阶段：建立失败优先的 targeted regression tests

### 4.1 测试原则

每个 top gap 都必须先有失败测试，再改实现。

测试必须验证：

1. candidate 能被抽出。
2. candidate 有 source_anchor。
3. candidate evidence 能解释来源。
4. candidate target field 正确。
5. forbidden pair 不会被 accepted。
6. LLM-only candidate 不会 accepted。
7. strict validator 接受标准化结果。
8. rerun evaluator 后 report 数值真实变化。

### 4.2 必须新增 / 扩展的测试组

测试文件名由 Codex 根据现有结构决定，建议如下：

```text
backend/tests/test_policy_candidate_extraction_phase_i.py
backend/tests/test_meeting_candidate_extraction_phase_i.py
backend/tests/test_general_mapping_ranking_phase_i.py
backend/tests/test_phase_i_review_subagent_gates.py
backend/tests/test_phase_i_deepseek_candidate_loop.py
backend/tests/test_phase_i_production_shadow_eval.py
```

### 4.3 测试样本选择

从 Phase H gap drilldown 中选最具代表性样本：

#### policy_doc

优先覆盖：

```text
publish_date
effective_date
valid_until
issuer
document_number
policy_measures
target_audience
summary
```

至少选择 8–10 个 policy real-world UIR。用 `rg` 查找：

```powershell
Get-ChildItem examples\real_world\uir\policy
rg "发布日期|发布时间|印发|发文|施行|有效期|发布单位|发文机关|政策措施|支持措施|适用对象|服务对象" examples\real_world\uir\policy -n
```

#### meeting_doc

优先覆盖：

```text
meeting_number
topics
organizer
attendees
meeting_date
decisions
action_items
```

至少选择 8–10 个 meeting UIR。查找：

```powershell
Get-ChildItem examples\real_world\uir\meeting
rg "第.*次|会议纪要|〔|\[|议题|研究|审议|决定|会议时间|主持|出席|列席|组织单位|办公室" examples\real_world\uir\meeting -n
```

#### general_doc

优先覆盖：

```text
application_conditions
contact
service_object
process_steps
application_materials
title
```

必须覆盖 Phase H subagent 已 approve 的 15 个 application_conditions 样本。

---

## 5. 第三阶段：候选抽取增强——policy_doc

policy_doc 是最大瓶颈。必须优先处理。

### 5.1 policy_doc.publish_date

#### 当前缺口

```text
policy_doc.publish_date: candidate_not_extracted x15
```

#### 目标

```text
candidate_not_extracted x15 -> <= 3
publish_date required missing -> <= 1
日期格式 invalid 不增加
badcase violations = 0
```

#### 需要支持的 source patterns

Codex 应实现 role-aware date candidate extractor。支持以下 label / context：

```text
发布日期：2026年7月1日
发布时间：2026-07-01
发文日期：2026年7月1日
印发日期：2026年7月1日
成文日期：2026年7月1日
发布于 2026年7月1日
YYYY年MM月DD日发布
YYYY-MM-DD 发布
```

#### 必须排除 / 降权的 false positives

```text
retrieved_at
抓取时间
更新时间
网页生成时间
有效期至
截止日期
申报截止时间
报名时间
受理时间
公示期
施行日期
自 YYYY 年 MM 月 DD 日起施行
```

#### 实现要求

为 date candidate 增加 role：

```json
{
  "source_label": "发布日期",
  "raw_value": "2026年7月1日",
  "normalized_value": "2026-07-01",
  "date_role": "publish_date",
  "target_field_hint": "publish_date",
  "source_anchor": "block/page/path/id",
  "evidence_type": "label_value|near_heading|metadata|body_context",
  "negative_context": []
}
```

#### 排序权重建议

```text
+100 exact label 发布日期 / 发布时间
+85 发文日期 / 印发日期 / 成文日期，且上下文为政策发布元信息
+70 title/header metadata line
+50 body sentence contains 发布/印发 and issuer nearby
-120 retrieved_at / 抓取时间 / 更新时间
-100 有效期至 / 截止 / 申报 / 报名 / 公示期
-80 自...起施行 / 施行日期，除非 target = effective_date
```

#### 测试要求

必须新增测试：

1. `发布日期` 映射 publish_date。
2. `发布时间` 映射 publish_date。
3. `发文日期` 在 policy metadata 中映射 publish_date。
4. `retrieved_at` 不映射 publish_date / effective_date。
5. `有效期至` 不映射 publish_date。
6. `自...起施行` 不映射 publish_date，应作为 effective_date 候选。
7. 中文日期标准化成 ISO 日期。

### 5.2 policy_doc.issuer

#### 当前缺口

```text
policy_doc.issuer: candidate_not_extracted x5
strict diagnostic issuer missing x9
```

#### 目标

```text
issuer missing field incidents <= 2
issuer candidate_not_extracted <= 1
承办单位/联系人/页面来源 不得自动 accepted 为 issuer
```

#### 支持 patterns

```text
发文机关：XX局
发布单位：XX委员会
印发单位：XX人民政府办公室
XX人民政府关于...
XX局关于印发...
由 XX局、XX委 联合发布
XX部门联合印发
```

#### 位置规则

优先级：

```text
1. 红头/标题上方机关行
2. 标题中 “XX关于...” 的 XX，且 XX 是政府/局/委/办/厅等组织后缀
3. 正文开头 “经 XX 批准 / 由 XX 印发 / XX 发布”
4. metadata label: 发布单位 / 发文机关 / 印发单位
5. 页脚/网站来源只作为弱证据，不可单独 auto-accept
```

#### forbidden / risk patterns

```text
承办单位
主办单位
协办单位
服务窗口
咨询单位
联系人
联系电话
技术支持
网站来源
转载来源
```

这些可以作为 `organization_candidate`，但不能直接 accepted 为 `issuer`，除非同一锚点附近存在 “发布/印发/发文机关” 强标签。

#### 测试要求

1. `发文机关：XX局` -> issuer accepted。
2. `XX人民政府办公室关于...` -> issuer accepted。
3. `承办单位：XX中心` -> issuer review_required 或 blocked，不 accepted。
4. `联系人：张三` -> 不进入 issuer。
5. 联合发文保留多个 issuer 或 join 成规范字符串，必须有 evidence。

### 5.3 policy_doc.effective_date / valid_until

#### 当前缺口

```text
policy_doc.effective_date: candidate_not_extracted x5
policy_doc.valid_until: candidate_not_extracted x3
date_format_invalid = 12
```

#### 目标

```text
effective_date candidate_not_extracted <= 1
valid_until candidate_not_extracted <= 1
date_format_invalid 12 -> <= 3
```

#### patterns

```text
自 YYYY年MM月DD日 起施行
自发布之日起施行
自印发之日起施行
本办法自 YYYY-MM-DD 起施行
有效期至 YYYY年MM月DD日
执行至 YYYY年MM月DD日
截止至 YYYY年MM月DD日
```

#### 规则

```text
自发布之日起施行：
  如果 publish_date 已 source-backed，则 effective_date = publish_date，evidence 必须引用 publish_date 的 source + 施行句 source。
  如果 publish_date 不存在，则 effective_date review_required，不能凭空补值。

有效期至 / 执行至 / 截止至：
  target = valid_until，不能映射 publish_date。
```

#### 测试要求

1. `自2026年7月1日起施行` -> effective_date = 2026-07-01。
2. `自发布之日起施行` + publish_date exists -> effective_date = publish_date，带 derivation evidence。
3. `有效期至2027年12月31日` -> valid_until。
4. `截止时间` 在申报上下文中不得映射 valid_until，除非 target field 是 application deadline 类型。

### 5.4 policy_doc.policy_measures

#### 当前缺口

```text
policy_doc.policy_measures: candidate_not_extracted x7
```

#### 目标

```text
policy_measures candidate_not_extracted <= 2
```

#### section headings

```text
政策措施
支持措施
扶持措施
主要措施
补贴标准
支持内容
奖励标准
资助方式
保障措施
重点任务
```

#### extraction behavior

政策措施通常不是一行 label-value，而是 section/list。候选应支持：

```json
{
  "target_field_hint": "policy_measures",
  "value_type": "section_text|list_items",
  "items": ["...", "..."],
  "source_anchor": "heading block + child blocks",
  "confidence_tier": "medium|high"
}
```

#### negative patterns

```text
申请条件
申报材料
办理流程
联系方式
政策依据
解读说明
```

这些不得混入 policy_measures。

### 5.5 policy_doc.target_audience / application_conditions / application_materials

#### target_audience patterns

```text
适用对象
服务对象
支持对象
申报对象
扶持对象
适用范围
面向对象
```

#### application_conditions patterns

```text
申请条件
申报条件
认定条件
准入条件
办理条件
支持条件
```

#### application_materials patterns

```text
申请材料
申报材料
提交材料
所需材料
材料清单
```

#### 要求

这些字段必须使用 section-aware extraction，不能只依赖表头。

---

## 6. 第四阶段：候选抽取增强——meeting_doc

### 6.1 meeting_doc.meeting_number

#### 当前缺口

Phase H drilldown 明细显示 15 个 meeting docs 的 meeting_number 都是 candidate_not_extracted，Review subagent 也全部 needs_human。

#### 目标

```text
meeting_number candidate_not_extracted 15 -> <= 4
subagent needs_human 15 -> <= 5
```

#### patterns

```text
第 N 次会议
第 N 次常务会议
第 N 次政府常务会议
第 N 期
会议纪要第 N 期
〔2026〕N号
[2026] N号
2026年第N次会议
N届N次会议
常务会议纪要（第N期）
```

#### extraction priority

```text
1. 标题中的 “第N次”
2. 标题附近 / metadata 中的 “会议纪要第N期”
3. 文号行中的 “〔YYYY〕N号”
4. 正文第一段 “召开第N次...”
```

#### value normalization

保留原始表达，但可附 normalized：

```json
{
  "raw_value": "第49次常务会议",
  "normalized_value": "49",
  "display_value": "第49次常务会议"
}
```

#### false positives

```text
第 N 条
第 N 项
第 N 页
N 月 N 日
议题 N
附件 N
```

这些不能映射 meeting_number。

### 6.2 meeting_doc.topics

#### 当前缺口

```text
meeting_doc.topics: candidate_not_extracted x7
```

#### patterns

```text
会议议题
研究事项
审议事项
会议研究了
会议听取了
会议审议了
会议原则同意
研究部署
```

#### extraction behavior

提取 topics 为 list：

```json
{
  "target_field_hint": "topics",
  "value_type": "list_items",
  "items": ["审议...", "研究...", "听取..."],
  "source_anchor": "topic section or decision paragraphs"
}
```

#### 区分 topics 与 decisions

```text
topics = 会议讨论/研究/审议的事项
decisions = 已形成的决定、原则同意、通过、要求
```

同一段可以同时生成 topics candidate 和 decisions candidate，但 evidence/ranking 必须区分 target。

### 6.3 meeting_doc.organizer

#### 当前缺口

```text
meeting_doc.organizer: candidate_not_extracted x6
```

#### patterns

```text
会议由 XX 主持召开
XX 组织召开
XX 主持会议
会议召集人：XX
组织单位：XX
```

#### 注意

`主持人` 不等于 `organizer`，除非 schema 允许 organizer 表示主持/组织者。若 schema 中 organizer 是组织单位，则个人主持人应 review_required 或映射到 host/chair 字段。必须查 schema 定义后实现。

### 6.4 meeting_doc.attendees

#### 当前缺口

```text
meeting_doc.attendees: candidate_not_extracted x5
meeting_doc.attendees: candidate_extracted_but_not_ranked x1
```

#### patterns

```text
出席：
参加：
列席：
参会人员：
与会人员：
```

#### forbidden

```text
主持人 -> attendees 禁止自动 accepted
联系人 -> attendees 禁止自动 accepted
```

#### extraction behavior

attendees 应优先来自列表/顿号/逗号分隔人名或组织名，不应从联系人中抽。

### 6.5 meeting_doc.decisions / action_items

#### decisions patterns

```text
会议决定
会议原则同意
会议审议通过
会议要求
会议强调
会议指出
```

#### action_items patterns

```text
由 XX 负责
请 XX 于 ... 前完成
下一步
抓好落实
推进实施
```

---

## 7. 第五阶段：general_doc evidence ranking 与 extraction

### 7.1 general_doc.application_conditions ranking

#### 当前情况

Phase H Review Subagent 批准了 15 个 `general_doc.application_conditions` 候选，但 Phase H Knowledge Growth 仍是 draft_only，且 evaluator 指标没有变化。

#### 目标

```text
general_doc.application_conditions ranking gap 15 -> <= 2
review subagent approved 15 -> active after gates >= 10
non_procurement recall 有可测 delta
```

#### 行动

1. 找出这 15 个候选在 mapping_report 中的当前 ranking 情况。
2. 增强 evidence ranking，使 source-backed application_conditions 超过泛化 summary/content/material/process candidates。
3. 将 approved candidates 进入 gated knowledge pack。
4. 激活 active pack 后重跑 evaluator。

#### scoring 建议

```text
+100 heading exact: 申请条件 / 申报条件 / 办理条件 / 受理条件
+80 nearby bullet/list under condition heading
+50 body contains “应当符合 / 需满足 / 条件如下”
-60 材料 / 资料 / 附件 / 清单
-60 流程 / 步骤 / 办理程序
-80 联系方式 / 电话 / 地址
```

### 7.2 general_doc.contact

#### 当前缺口

```text
general_doc.contact: candidate_not_extracted x6
```

#### patterns

```text
联系电话
咨询电话
联系方式
联系人
咨询方式
受理地址
办公地址
邮箱
```

#### schema 对齐

如果 `contact` 允许结构化对象，保留：

```json
{
  "person": "...",
  "phone": "...",
  "email": "...",
  "address": "..."
}
```

如果 schema 只允许 string，渲染为稳定字符串，同时 metadata 保存结构化 evidence。

### 7.3 general_doc.service_object

#### 当前缺口

```text
general_doc.service_object: candidate_not_extracted x6
```

#### patterns

```text
服务对象
适用对象
办理对象
受理对象
申请人
申请主体
面向对象
```

必须保持与 `application_conditions` 区分：

```text
service_object = 谁可以办理 / 面向谁
application_conditions = 需要满足什么条件
```

### 7.4 general_doc.process_steps / application_materials

使用 section heading extraction：

```text
办理流程 / 办理程序 / 申请流程 / 操作步骤 -> process_steps
申请材料 / 所需材料 / 材料清单 / 提交材料 -> application_materials
```

---

## 8. 第六阶段：统一候选抽取框架改造

如果现有代码是按 schema 分散写规则，本轮建议抽象一个 `DocumentFamilyCandidateExtractor` 或等价结构，避免继续堆散乱 if。

### 8.1 Candidate model 扩展

每个候选至少包含：

```json
{
  "candidate_id": "stable id",
  "doc_id": "...",
  "doc_type": "policy_doc|meeting_doc|general_doc",
  "target_field_hint": "publish_date",
  "source_label": "发布日期",
  "raw_value": "2026年7月1日",
  "normalized_value": "2026-07-01",
  "value_type": "date|string|list|section_text|object",
  "source_anchor": {
    "block_id": "...",
    "path": "...",
    "page": null,
    "offset": null
  },
  "evidence": [
    {
      "type": "label_value|heading_section|title_pattern|body_context|metadata",
      "text": "...",
      "score": 100
    }
  ],
  "risk_flags": [],
  "negative_context": [],
  "date_role": "publish_date|effective_date|valid_until|null",
  "confidence": 0.0,
  "confidence_tier": "high|medium|low",
  "proposed_by": "deterministic|deepseek|review_subagent",
  "review_state": "auto_eligible|review_required|blocked"
}
```

### 8.2 Heading-aware section extraction

实现或增强以下通用能力：

```text
extract_heading_sections(blocks)
match_heading_aliases(section.heading, target_field_aliases)
collect_child_blocks_until_next_same_or_higher_heading(section)
normalize_list_items(section.blocks)
create_section_candidate(target_field, section)
```

适用于：

```text
policy_measures
target_audience
application_conditions
application_materials
process_steps
topics
decisions
action_items
```

### 8.3 Label-value extraction

支持：

```text
Label: Value
Label：Value
Label Value
【Label】Value
（Label）Value
```

### 8.4 Title / metadata extraction

对政策和会议文档，很多字段在标题或 metadata 中：

```text
XX人民政府关于印发...的通知 -> issuer candidate
第N次政府常务会议纪要 -> meeting_number candidate
YYYY年MM月DD日 -> publish_date / meeting_date，需上下文 role
```

---

## 9. 第七阶段：Evidence Ranking 统一改造

### 9.1 当前问题

有些字段 candidate 已经抽出，但没有排到正确 target，例如 `general_doc.application_conditions`。

### 9.2 统一 scoring formula

建议综合：

```text
score =
  label_score
+ heading_score
+ source_anchor_score
+ value_type_score
+ doc_family_prior_score
+ section_position_score
+ date_role_score
+ source_quality_score
- negative_context_penalty
- badcase_penalty
- ambiguity_penalty
- llm_only_penalty
```

### 9.3 基础权重

```text
label_score:
  exact schema alias = +100
  known safe synonym = +80
  weak synonym = +40

heading_score:
  section heading exact = +90
  child of matching heading = +70
  nearby heading within 2 blocks = +40

source_anchor_score:
  block/path present = +30
  line/context present = +20
  no source anchor = -200 and not auto eligible

value_type_score:
  expected date and parseable ISO date = +40
  expected list and list extracted = +30
  expected section text and section extracted = +25
  type mismatch = -80

date_role_score:
  target matches date_role = +80
  target conflicts date_role = -120

negative_context_penalty:
  forbidden label = -200 and blocked
  unrelated section = -80
  generic content = -40

llm_only_penalty:
  deepseek candidate without deterministic evidence = -200 and review_required
```

### 9.4 Auto acceptance rules

Only auto accept if all conditions are true:

```text
source_anchor exists
badcase_filter not hit
not LLM-only
confidence_tier high or approved_by_review_subagent
expected value type valid
no forbidden negative context
schema field not ambiguous under current doc family
```

### 9.5 Review-required rules

Force review if:

```text
candidate is medium confidence fuzzy
candidate source label appears in forbidden pair registry
candidate is DeepSeek-only
candidate has no source anchor
candidate maps organization to issuer but label is 承办单位/主办单位/联系人/网站来源
candidate maps person/host/contact to attendees
candidate maps retrieved_at/update_time to publish/effective date
```

---

## 10. 第八阶段：Review Subagent 模拟人工审查闭环

Phase H 做了 subagent review，但没有让指标生效。本轮必须补闭环。

### 10.1 Subagent 分工

实现或模拟 6 类 reviewer。可以是代码中的 deterministic reviewers，也可以是脚本中的独立审查模块。

#### 1. ExtractorAuditor

职责：判断 candidate 是否有足够 source evidence。

输出：

```json
{
  "reviewer": "ExtractorAuditor",
  "decision": "pass|fail",
  "reason": "source_anchor exists and section heading matches target alias"
}
```

#### 2. EvidenceJudge

职责：判断 candidate 是否语义对应 target field。

重点区分：

```text
publish_date vs effective_date vs valid_until vs retrieved_at
issuer vs organizer vs contractor vs contact
attendees vs host/contact
application_conditions vs application_materials vs process_steps
policy_measures vs policy_basis/summary
```

#### 3. BadcaseGuard

职责：强制检查 forbidden pairs。

任何 forbidden hit：

```text
decision = reject 或 blocked
```

#### 4. SchemaValidatorReviewer

职责：验证 normalized_value 是否满足 schema 类型、必填、值域。

#### 5. KnowledgeCurator

职责：判断候选是否适合沉淀为 alias / extraction rule / ranking rule。

#### 6. ReportConsistencyAuditor

职责：确认应用候选后 evaluator 指标真实变化，且没有修改报告作弊。

### 10.2 Subagent decision schema

每条决策必须写入结构化报告：

```json
{
  "doc_id": "real_policy_xxx",
  "doc_type": "policy_doc",
  "target_field": "publish_date",
  "candidate_id": "...",
  "candidate_value": "2026-07-01",
  "source_anchor": "...",
  "candidate_origin": "deterministic|deepseek|knowledge",
  "subagent_votes": [
    {"agent": "ExtractorAuditor", "decision": "pass", "reason": "..."},
    {"agent": "EvidenceJudge", "decision": "pass", "reason": "..."},
    {"agent": "BadcaseGuard", "decision": "pass", "reason": "..."},
    {"agent": "SchemaValidatorReviewer", "decision": "pass", "reason": "..."}
  ],
  "final_decision": "approve|reject|needs_human|blocked",
  "approval_type": "simulated_human_approved",
  "eligible_for_active_pack": true,
  "must_not_count_as_llm_auto_accepted": true
}
```

### 10.3 Approval rule

Approve only if:

```text
ExtractorAuditor = pass
EvidenceJudge = pass
BadcaseGuard = pass
SchemaValidatorReviewer = pass
source_anchor exists
candidate_origin != deepseek OR deterministic evidence verifies it
```

Needs human if:

```text
source evidence incomplete
candidate is ambiguous
date role conflict remains
organization role unclear
```

Reject if:

```text
forbidden pair hit
source contradicts target
value type invalid
```

### 10.4 From approved candidate to active knowledge

本轮必须打通：

```text
candidate approved by subagent
-> create review record with status approved and actor=simulated_human_reviewer
-> create knowledge candidate
-> add to draft knowledge pack
-> run impact preview
-> run badcase gates
-> activate pack only if gates pass
-> rerun evaluator
```

关键约束：

```text
llm_auto_accepted_count must remain 0
approved_by_subagent must not be classified as llm_auto_accepted
old task snapshots must remain unchanged
```

### 10.5 预期指标

本阶段至少应让：

```text
general_doc.application_conditions 15 个 approved candidates 生效 >= 10 个
review_required_field_count 下降
semantic_quality_average_recall 有非零提升
```

---

## 11. 第九阶段：DeepSeek 候选建议闭环

Phase H 中 DeepSeek no-op，因为 key 未配置。本轮如果可以配置 key，应实际启用；如果环境不能配置 key，也必须保留 graceful no-op，但不要把它作为指标提升主路径。

### 11.1 安全配置

DeepSeek key 只能来自环境变量或本地 `.env`，不能写入代码、报告、snapshot、task options。

```powershell
$env:DEEPSEEK_API_KEY="<local only>"
```

或使用项目既有 provider 配置方式。

### 11.2 DeepSeek 使用范围

只允许对以下 gap rows 调用：

```text
candidate_not_extracted
candidate_extracted_but_not_ranked
```

优先级：

```text
1. policy_doc.publish_date
2. policy_doc.issuer
3. policy_doc.effective_date
4. policy_doc.policy_measures
5. policy_doc.target_audience
6. meeting_doc.meeting_number
7. meeting_doc.topics
8. general_doc.application_conditions ranking
```

### 11.3 DeepSeek 输入最小化

输入只包含必要上下文：

```json
{
  "doc_type": "policy_doc",
  "target_field": "publish_date",
  "field_definition": "policy publication date, not effective date or crawl time",
  "allowed_output": "candidate proposal only",
  "blocks": [
    {"block_id": "...", "text": "...", "heading_path": ["..."], "metadata": {}}
  ],
  "forbidden_pairs": [
    {"source": "retrieved_at", "target": "effective_date"},
    {"source": "发布日期", "target": "effective_date"}
  ]
}
```

不要发送 secrets、API keys、完整环境变量、用户凭证。

### 11.4 DeepSeek prompt 模板

```text
你是数据治理字段映射候选生成器。只生成候选，不要做最终接受。

目标字段：{target_field}
字段定义：{field_definition}
文档类型：{doc_type}
安全规则：
- 只有原文中有明确证据的值才能提出。
- retrieved_at、抓取时间、更新时间不能作为发布日期或生效日期。
- 承办单位、联系人、服务窗口不能作为 issuer，除非原文明确写“发文机关/发布单位/印发单位”。
- 主持人、联系人不能作为 attendees。
- 输出必须包含 source block id 和原文片段。
- 如果证据不足，返回 no_candidate。

请返回 JSON，schema 如下：
{
  "candidates": [
    {
      "target_field": "...",
      "raw_value": "...",
      "normalized_value": "...",
      "source_block_id": "...",
      "source_quote": "...",
      "evidence_reason": "...",
      "risk_flags": [],
      "confidence": 0.0
    }
  ],
  "no_candidate_reason": null
}
```

### 11.5 DeepSeek 输出处理

DeepSeek 输出必须经过：

```text
JSON schema validation
source_quote exists in source block
source_block_id exists
badcase guard
deterministic evidence verifier
review subagent
schema validator
```

只有全部通过后：

```text
candidate_origin = deepseek
review_state = simulated_human_approved
llm_auto_accepted_count remains 0
```

DeepSeek candidate 不能直接写 accepted mapping。

### 11.6 DeepSeek 报告指标

新增 / 更新：

```text
reports/phase_i_deepseek_review_loop_report.json
reports/phase_i_deepseek_review_loop_report.md
```

必须包含：

```text
deepseek_configured
deepseek_requests
deepseek_candidates
evidence_linked_candidates
subagent_reviewed
subagent_approved
subagent_rejected
needs_human
applied_to_draft_pack
activated_after_gates
badcase_violations
llm_auto_accepted_count
secret_leaks
snapshot_mutations
measurable_recall_delta
strict_pass_delta
```

成功标准：

```text
如果 DeepSeek key 配置：
  deepseek_requests > 0
  evidence_linked_candidates > 0
  subagent_reviewed > 0
  llm_auto_accepted_count = 0
  badcase_violations = 0
  measurable_recall_delta >= 0

如果 DeepSeek key 未配置：
  status = no_op
  不得把 DeepSeek 作为完成 0.85 的依据
```

---

## 12. 第十阶段：Knowledge Pack 激活与快照保护

### 12.1 当前问题

Phase H 中：

```text
Knowledge activation = 0 activated
Draft candidates = general_doc.application_conditions draft_only
```

导致指标无变化。

### 12.2 本轮目标

```text
approved deterministic/review candidates -> active knowledge pack
old_snapshot_unchanged = True
badcase_violations = 0
rejected_candidates_activated = 0
```

### 12.3 激活流程

Codex 应使用已有 Review/Knowledge APIs 或服务层，不要绕过治理表。

```text
1. collect approved candidates
2. create knowledge candidates
3. create draft pack
4. attach candidates to draft pack
5. run impact preview on target evaluator set
6. run badcase registry checks
7. run snapshot preservation checks
8. activate pack
9. rerun evaluator from clean task creation / future task path
10. compare before/after metrics
```

### 12.4 Active pack 分类

建议拆成多个小 pack，方便 rollback：

```text
phase_i_general_application_conditions_pack
phase_i_policy_dates_pack
phase_i_policy_issuer_pack
phase_i_policy_sections_pack
phase_i_meeting_metadata_pack
phase_i_meeting_topics_pack
```

每个 pack 都应有：

```json
{
  "name": "phase_i_policy_dates_pack",
  "created_by": "phase_i_codex",
  "approval_mode": "simulated_human_approved_after_gates",
  "source_report": "reports/phase_i_review_subagent_report.json",
  "badcase_gate": "passed",
  "impact_preview": "passed"
}
```

### 12.5 快照不变测试

必须验证历史 task snapshot 未改变：

```text
metadata bytes/structure unchanged
canonical bytes/structure unchanged
mapping_report bytes/structure unchanged
execution_snapshot bytes/structure unchanged
```

---

## 13. 第十一阶段：Strict Validation 修复

### 13.1 当前失败

Phase H / G strict diagnostic 中仍存在：

```text
Validation passed = 39
Validation failed = 11
Required missing fields = 14
Review-required fields = 22
Failure categories:
  date_format_invalid = 12
  missing_required = 18
  semantic_review_required = 22
```

### 13.2 目标

```text
strict_pass 39/50 -> >= 43/50，冲刺 >=45/50
date_format_invalid 12 -> <= 3
missing_required 18 -> <= 5
semantic_review_required 22 -> <= 12
```

### 13.3 日期标准化

实现统一 date normalizer：

输入支持：

```text
2026年7月1日
2026 年 07 月 01 日
2026-7-1
2026/07/01
2026.07.01
二〇二六年七月一日
2026年7月
```

输出：

```text
YYYY-MM-DD
YYYY-MM，如果 schema 允许 month precision；否则 review_required
```

必须保留 raw_value 和 normalized_value。

### 13.4 Required missing 修复

不得用默认值伪造。只允许：

```text
source-backed direct extraction
source-backed derivation，例如 effective_date = publish_date only when “自发布之日起施行” exists
review-approved knowledge rule
```

### 13.5 Review-required 降低

只通过以下方式降低：

```text
更强 exact/heading evidence
更强 date role classifier
更强 negative context 排除
subagent simulated approval
active knowledge pack
```

不得通过降低 threshold 或关闭 review-required。

---

## 14. 第十二阶段：Production Shadow Blind Corpus

### 14.1 当前问题

Phase H production shadow：

```text
Blind docs = 0
Gold labels = 0
Can claim 0.85 = False
```

### 14.2 本轮最低目标

建立最小可跑的 blind smoke corpus：

```text
examples/production_shadow/manifest.json
examples/production_shadow/uir/*.json
examples/production_shadow/gold/mapping_gold.jsonl
examples/production_shadow/gold/badcases.jsonl
```

至少：

```text
10 blind docs
其中 policy >= 4
meeting >= 3
general >= 3
gold labels 覆盖 title + required fields + top gap fields
badcases 覆盖 date/issuer/attendees/contact 等高风险项
```

### 14.3 数据来源要求

如果当前 workspace 无外部新数据，允许从现有 examples 构造 blind smoke，但必须：

```text
1. 与当前 50/60 evaluator corpus 去重，优先新增样本。
2. 如果无法完全去重，报告必须标记为 shadow_smoke_not_production_claim。
3. manifest 记录 source、hash、doc_type、gold label count。
4. 不允许用 evaluator outputs 自动生成 gold。
5. gold labels 必须人工/模拟人工审查确认，记录 reviewer。
```

### 14.4 Gold schema

`mapping_gold.jsonl` 建议：

```json
{"doc_id":"shadow_policy_001","doc_type":"policy_doc","target_field":"publish_date","expected_value":"2026-07-01","source_anchor":"block:metadata_1","evidence_quote":"发布日期：2026年7月1日","required":true}
{"doc_id":"shadow_policy_001","doc_type":"policy_doc","target_field":"issuer","expected_value":"XX人民政府办公室","source_anchor":"block:title_0","evidence_quote":"XX人民政府办公室关于...","required":true}
```

### 14.5 Evaluation script

如果已有 blocker script，扩展它：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_production_shadow.py `
  --base-url http://127.0.0.1:8000 `
  --manifest examples\production_shadow\manifest.json `
  --gold examples\production_shadow\gold\mapping_gold.jsonl `
  --out reports\phase_i_production_shadow_eval_report.json `
  --markdown reports\phase_i_production_shadow_eval_report.md
```

如果脚本不存在，Codex 应实现最小 evaluator：

```text
load manifest
load gold labels
import UIR
create task with doc_type schema/template
execute
read mapping report
compute per-doc recall
compute required missing
compute badcase violations
compute package verification
write report
```

### 14.6 Claim boundary

如果 blind docs < 30，报告必须写：

```text
This is a production shadow smoke evaluation, not enough to claim full production 0.85.
```

但不能继续是 empty blocker。

---

## 15. 第十三阶段：Gap Burn-down Dashboard

Codex 应新增一个可重复生成的 gap burn-down 报告：

```text
reports/phase_i_gap_burndown_report.json
reports/phase_i_gap_burndown_report.md
```

### 15.1 报告内容

```text
Baseline gaps by field
Current gaps by field
Fixed gaps by field
New regressions by field
Recall contribution estimate
Strict pass contribution
Review-required reduction
Badcase status
```

### 15.2 示例表

| Field | Baseline gaps | Current gaps | Fixed | New regressions | Status |
|---|---:|---:|---:|---:|---|
| policy_doc.publish_date | 15 | 4 | 11 | 0 | improved |
| meeting_doc.meeting_number | 15 | 5 | 10 | 0 | improved |
| general_doc.application_conditions | 15 | 2 | 13 | 0 | improved |

### 15.3 Hard gate

如果某字段出现新 regression：

```text
new_regressions > 0
```

必须在 acceptance report 中列出，不得隐藏。

---

## 16. 第十四阶段：最终验收命令

Codex 完成修改后，必须按顺序运行。

### 16.1 单元测试与全量验证

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
Push-Location frontend
npm.cmd test
Pop-Location
```

### 16.2 API-backed evaluators

启动 backend：

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

另开终端：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --timeout 60 `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\phase_i_non_procurement_mapping_eval_report.json `
  --markdown reports\phase_i_non_procurement_mapping_eval_report.md

backend\.venv\Scripts\python.exe scripts\eval_semantic_mapping_quality.py `
  --out reports\phase_i_semantic_mapping_quality_report.json `
  --markdown reports\phase_i_semantic_mapping_quality_report.md

backend\.venv\Scripts\python.exe scripts\eval_strict_validation_failure_analysis.py `
  --out reports\phase_i_strict_validation_failure_analysis.json `
  --markdown reports\phase_i_strict_validation_failure_analysis.md
```

如脚本名不同，Codex 用现有 Phase H 生成脚本替换。

### 16.3 Review / DeepSeek / Knowledge reports

```powershell
backend\.venv\Scripts\python.exe scripts\eval_phase_i_review_subagent.py `
  --out reports\phase_i_review_subagent_report.json `
  --markdown reports\phase_i_review_subagent_report.md

backend\.venv\Scripts\python.exe scripts\eval_phase_i_deepseek_review_loop.py `
  --out reports\phase_i_deepseek_review_loop_report.json `
  --markdown reports\phase_i_deepseek_review_loop_report.md

backend\.venv\Scripts\python.exe scripts\eval_phase_i_review_knowledge_growth.py `
  --out reports\phase_i_review_knowledge_growth_report.json `
  --markdown reports\phase_i_review_knowledge_growth_report.md
```

### 16.4 Shadow eval

```powershell
backend\.venv\Scripts\python.exe scripts\eval_production_shadow.py `
  --base-url http://127.0.0.1:8000 `
  --manifest examples\production_shadow\manifest.json `
  --gold examples\production_shadow\gold\mapping_gold.jsonl `
  --out reports\phase_i_production_shadow_eval_report.json `
  --markdown reports\phase_i_production_shadow_eval_report.md
```

### 16.5 Consistency / acceptance

```powershell
backend\.venv\Scripts\python.exe scripts\build_phase_i_mapping_gap_drilldown.py `
  --out reports\phase_i_mapping_gap_drilldown.json `
  --markdown reports\phase_i_mapping_gap_drilldown.md

backend\.venv\Scripts\python.exe scripts\build_phase_i_gap_burndown_report.py `
  --baseline reports\phase_h_mapping_gap_drilldown.json `
  --current reports\phase_i_mapping_gap_drilldown.json `
  --out reports\phase_i_gap_burndown_report.json `
  --markdown reports\phase_i_gap_burndown_report.md

backend\.venv\Scripts\python.exe scripts\check_phase_i_report_consistency.py `
  --out reports\phase_i_report_consistency.json `
  --markdown reports\phase_i_report_consistency.md

backend\.venv\Scripts\python.exe scripts\build_phase_i_acceptance_report.py `
  --out reports\phase_i_acceptance_report.json `
  --markdown reports\phase_i_acceptance_report.md
```

---

## 17. 最终验收标准

### 17.1 必须满足

```text
verify_all.py --check-openapi passed
frontend npm test passed
package_verification = 50/50
badcase_violations = 0
llm_auto_accepted_count = 0
secret_leaks = 0
old_snapshot_unchanged = True
report_consistency = passed
```

### 17.2 0.85 local target

必须至少满足：

```text
non_procurement_average_recall >= 0.85
strict_pass >= 43/50
required_missing_doc_count <= 1
```

如果 semantic_quality_average_recall 未到 0.85，但 non_procurement 到 0.85，则 acceptance report 必须解释口径差异，并继续列为 remaining risk。

### 17.3 不允许的验收话术

不能写：

```text
生产 blind recall 已达到 0.85
DeepSeek 自动提升了 mapping 并已接受
LLM 自动完成字段映射
Package pass 证明字段语义完全正确
```

除非对应报告真实证明。

### 17.4 允许的验收话术

如果 local 达标，可写：

```text
Phase I local 50-sample non-procurement evaluator reached average mapping recall >= 0.85 under zero badcase violations and zero LLM auto-accepted mappings.
```

如果 production shadow 只是 smoke，可写：

```text
A minimal production shadow smoke corpus was added and evaluated, but it is not large enough for a full production 0.85 claim.
```

---

## 18. 风险与应急策略

### 18.1 如果时间只够修 3 件事

优先级：

```text
1. policy_doc.publish_date extraction + date normalization
2. meeting_doc.meeting_number extraction
3. general_doc.application_conditions approved candidates -> active knowledge + ranking
```

原因：

```text
这三项覆盖最多 gap，且多数是 low-risk / source-backed，可快速提升 recall。
```

### 18.2 如果 DeepSeek 不可用

不要阻塞主线。DeepSeek 只是候选建议加速器，不是核心依赖。

执行：

```text
DeepSeek report status = no_op
主线继续用 deterministic extraction + review subagent + active knowledge
```

### 18.3 如果 recall 到 0.82–0.84 卡住

继续打：

```text
policy_doc.policy_measures
policy_doc.target_audience
policy_doc.issuer
policy_doc.effective_date
meeting_doc.topics
meeting_doc.organizer
general_doc.contact/service_object
```

不要调低阈值。

### 18.4 如果 strict pass 卡在 42/50

优先看 strict failure report：

```text
date_format_invalid
missing_required
semantic_review_required
```

修日期标准化和 required missing，通常比修长尾 recall 更快提升 strict pass。

### 18.5 如果 new badcase violation 出现

立刻回滚相关 rule / active pack。

必须生成：

```text
reports/phase_i_badcase_regression_analysis.md
```

内容：

```text
violating source/target
introduced by which rule/pack
rollback action
post-rollback verification
```

---

## 19. Codex 最终交付清单

Codex 完成后必须交付：

### 19.1 代码

```text
candidate extraction enhancements
ranking enhancements
review subagent gated activation
DeepSeek evidence-linked loop
strict validation normalization fixes
production shadow evaluator/corpus
report consistency scripts
```

### 19.2 测试

```text
policy candidate tests
meeting candidate tests
general ranking tests
badcase regression tests
review subagent tests
DeepSeek no-op/configured tests
knowledge activation snapshot tests
production shadow evaluator tests
```

### 19.3 报告

```text
reports/phase_i_non_procurement_mapping_eval_report.json/.md
reports/phase_i_semantic_mapping_quality_report.json/.md
reports/phase_i_strict_validation_failure_analysis.json/.md
reports/phase_i_mapping_gap_drilldown.json/.md
reports/phase_i_gap_burndown_report.json/.md
reports/phase_i_review_subagent_report.json/.md
reports/phase_i_deepseek_review_loop_report.json/.md
reports/phase_i_review_knowledge_growth_report.json/.md
reports/phase_i_production_shadow_eval_report.json/.md
reports/phase_i_report_consistency.json/.md
reports/phase_i_acceptance_report.json/.md
```

### 19.4 Acceptance summary

必须包含：

```text
baseline vs current metrics
what code changed
which gaps were fixed
which gaps remain
strict validation changes
badcase/LLM/secret safety
production shadow status
commands run and outputs
claim boundary
```

---

## 20. 最终提醒

本轮已经接近项目截止，优先级必须从“解释为什么未达标”转为“真实消除 gap”。

最应该立刻做的是：

```text
1. 修 policy_doc.publish_date：x15 最大缺口。
2. 修 meeting_doc.meeting_number：明细覆盖 15 个会议样本。
3. 让 general_doc.application_conditions subagent approved candidates 真正进入 active knowledge/ranking。
4. 修 policy_doc.policy_measures / target_audience / issuer / effective_date。
5. 重跑 evaluator，以 reports 真实指标为准。
```

成功的标志不是新增多少报告，而是：

```text
average_recall >= 0.85
strict_pass >= 43/50
badcase_violations = 0
llm_auto_accepted_count = 0
secret_leaks = 0
report_consistency = passed
```

如果达不到，acceptance report 必须诚实写明剩余差距和阻断原因，不能伪造生产 0.85 claim。
