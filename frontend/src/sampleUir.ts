export const sampleUir = {
  uir_version: "1.0",
  doc_id: "frontend_policy_demo_001",
  source: {
    source_type: "normalized_uir",
    source_name: "frontend_policy_demo_001",
    upstream_agents: ["uir_builder"]
  },
  metadata: {
    domain: "policy_doc",
    "标题": "公共数据接口开放管理办法",
    "发文机关": "市数据管理局",
    "发布日期": "2024-03-12",
    "政策类型": "办法",
    "关键词": ["公共数据", "接口", "开放"]
  },
  blocks: [
    {
      block_id: "fpd_b001",
      type: "heading",
      level: 1,
      text: "公共数据接口开放管理办法",
      attributes: {}
    },
    {
      block_id: "fpd_b002",
      type: "paragraph",
      text: "为规范公共数据接口开放、申请、调用和审计流程，制定本办法。",
      attributes: { field_name: "正文" }
    },
    {
      block_id: "fpd_b003",
      type: "table",
      text: null,
      attributes: {
        rows: [
          { field: "标题", value: "公共数据接口开放管理办法" },
          { field: "发文机关", value: "市数据管理局" },
          { field: "发布日期", value: "2024-03-12" }
        ]
      }
    }
  ],
  assets: [],
  normalization_records: []
};

export const sampleUirText = JSON.stringify(sampleUir, null, 2);
