import { mappingTone } from "../evidence";
import type { MappingReport } from "../types";

export type MappingEvidencePanelProps = { report: MappingReport | null };

function sourceName(item: Record<string, any>) {
  const source = item.source_field;
  return source && typeof source === "object" ? String(source.source_name ?? "-") : "-";
}

function evidenceText(item: Record<string, any>): string[] {
  if (Array.isArray(item.evidence_text)) {
    return item.evidence_text.map(String);
  }
  if (Array.isArray(item.evidence)) {
    return item.evidence.map((entry) =>
      entry && typeof entry === "object" ? String(entry.message ?? entry.type) : String(entry)
    );
  }
  return [];
}

export function MappingEvidencePanel({ report }: MappingEvidencePanelProps) {
  if (!report) {
    return <div className="empty-state">暂无 Mapping 证据。</div>;
  }
  const rows = [...report.review_required_items, ...report.mappings];
  return (
    <div className="evidence-panel mapping-evidence-panel">
      <div className="evidence-panel-head">
        <span>{report.mappings.length} 已接受</span>
        <span>{report.review_required_items.length} 待 Review</span>
        <span>{report.unmapped.length} 未映射</span>
      </div>
      {rows.map((item, index) => (
        <details className={`evidence-row tone-${mappingTone(item)}`} key={`${item.mapping_id}-${index}`}>
          <summary>
            <span>{sourceName(item)}</span>
            <strong>{String(item.target_field_id ?? "-")}</strong>
            <em>{displayConfidence(String(item.confidence_tier ?? item.status ?? "review"))}</em>
          </summary>
          <p>{String(item.review_required_reason ?? item.reason ?? "已保留证据。")}</p>
          {Array.isArray(item.risk_flags) && item.risk_flags.length ? (
            <div className="pill-row">
              {item.risk_flags.map((flag: string) => <span key={flag}>{flag}</span>)}
            </div>
          ) : null}
          <ul>
            {evidenceText(item).map((text, textIndex) => (
              <li key={`${text}-${textIndex}`}>{text}</li>
            ))}
          </ul>
        </details>
      ))}
    </div>
  );
}

function displayConfidence(value: string) {
  const labels: Record<string, string> = {
    high: "高",
    medium: "中",
    low: "低",
    accepted: "已接受",
    review: "待 Review"
  };
  return labels[value.toLowerCase()] ?? value;
}
