# 非采购 Mapping 深化验收报告

本报告覆盖扩展后 45-document real-world dataset 中的 35-document 非采购子集。

## Before / After

| Metric | 深化前隔离基线 | 深化后干净数据库 | 目标 | 状态 |
| --- | ---: | ---: | ---: | --- |
| Documents | 20 | 35 | 扩展到至少 35 | 达标 |
| Average mapping recall | `0.4032738095238095` | `0.5677551020408163` | `>= 0.55` | 达标 |
| Review-required | 147 | 69 | `<= 120` | 达标 |
| Required missing | 11 | 6 | `<= 6` | 达标 |
| Badcase violations | 0 | 0 | `0` | 达标 |
| Package verification | 20/20 | 35/35 | 全部通过 | 达标 |

## Per document type

| Doc type | Documents | Average recall | Review-required | Required missing | Packages |
| --- | ---: | ---: | ---: | ---: | ---: |
| `general_doc` | 10 | `0.6291666666666667` | 31 | 0 | 10/10 |
| `meeting_doc` | 10 | `0.4341666666666667` | 17 | 0 | 10/10 |
| `policy_doc` | 15 | `0.6158730158730158` | 21 | 6 | 15/15 |

## 实施内容

- 扩展 15 个公开官方 HTML/text-layer PDF 样本，并同步维护 manifest、UIR、gold、badcase、retrieval query 与 review fixture。
- 增强通用申报段落、会议首段日期/编号/主持人、政策落款机构和官方网页发布日期候选。
- 为三类非采购模板加入可追溯 `source_url` aliases。
- 将 fuzzy review 最低相似度从 0.45 收紧到 0.55；模糊匹配仍不自动接受。
- 删除 `成文日期 -> publish_date` 和无条件 `发布机构 -> issuer` 的高风险 aliases。

## Remaining gaps

- Meeting recall 仍低于其他类型，主要缺口是 topics、decisions、attendees 和 location 的自然段语义抽取。
- Policy 仍有 3 个 issuer 和 3 个 publish-date 必填缺失；没有使用成文日期或来源站点猜测来换取更低 missing count。
- Package verification 只证明结构、hash、parseability 与 traceability，不等同于所有字段语义 strict-pass。

## 结论

本轮非采购深化 gate 通过。结果保持 `badcase violations = 0`，没有通过放宽 required fields 或把低置信度 fuzzy 自动接受来换取指标。
