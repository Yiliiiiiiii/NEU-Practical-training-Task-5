# Product

## Register

product

## Users

SchemaPack Agent 面向需要把规范化文档转换为受 Schema 约束成果包的开发者、评测人员和审核人员。用户在工作台中检查数据集、执行记录、字段映射、风险项与回归门，并需要快速判断结果是否可信、是否可复现、是否仍需人工 Review。

## Product Purpose

产品以标准 UIR / External UIR JSON 为生产边界，通过确定性
Mapping、Transform、Validation、Manifest 和 Package Verification 生成成果包，
并通过 SchemaPack-Lineage 记录字段、chunk 与 artifact 的来源和决策链路。
成功不仅意味着结构可解析，还意味着语义校验、badcase safety、LLM 不自动接受、
lineage 安全和回归门状态被清楚地区分与展示。

## Brand Personality

清晰、克制、可信。界面语气应像严谨的工程验收工具：直接解释指标和风险，不夸大能力，不用视觉效果掩盖不确定性。

## Anti-references

- 不做装饰性大屏、夸张动效或无意义的 KPI 炫技。
- 不把 Package Verification 与 strict semantic validation 混为一谈。
- 不只依赖颜色表达状态；状态必须有可读文字。
- 不把 LLM suggestion、Schema Draft 或高风险映射表现成已自动生效。

## Design Principles

1. 安全状态优先于漂亮数字。
2. 每个结论都能追溯到数据集、执行记录、报告或复现命令。
3. 将通过、需关注、失败三种状态写清楚，并解释原因。
4. 保持信息密度，但用稳定层级降低扫描成本。
5. 对降级、缺失和未实现能力如实提示。

## Accessibility & Inclusion

保持键盘可操作和可见焦点，正文与背景满足 WCAG AA 对比度；状态同时使用文字、图标和颜色；窄屏下保持结构可读；不加入依赖动效才能理解的信息。
