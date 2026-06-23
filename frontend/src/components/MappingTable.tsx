import { CheckCircle2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { MappingListItem } from "../api/types";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { MethodBadge } from "./MethodBadge";
import { StatusBadge } from "./StatusBadge";

interface MappingTableProps {
  mappings: MappingListItem[];
  targetFields: string[];
  candidateSamples?: Record<string, string>;
  onReview: (mapping: MappingListItem, targetFieldId: string) => void | Promise<void>;
}

function labelForStatus(mapping: MappingListItem): string {
  if (mapping.need_review) {
    return "需审核";
  }
  if (mapping.status === "confirmed") {
    return "已确认";
  }
  return mapping.status;
}

export function MappingTable({
  mappings,
  targetFields,
  candidateSamples = {},
  onReview,
}: MappingTableProps) {
  const [draftTargets, setDraftTargets] = useState<Record<string, string>>({});

  useEffect(() => {
    setDraftTargets(
      Object.fromEntries(mappings.map((mapping) => [mapping.mapping_id, mapping.target_field_id])),
    );
  }, [mappings]);

  const fallbackTargetFields = useMemo(
    () =>
      Array.from(
        new Set([
          ...targetFields,
          ...mappings.map((mapping) => mapping.target_field_id).filter(Boolean),
        ]),
      ),
    [mappings, targetFields],
  );

  if (!mappings.length) {
    return (
      <div className="empty-state">
        <strong>暂无 Mapping。</strong>
        <span>生成候选字段并执行 Mapping 后，这里会显示审核行。</span>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>源字段 Source</th>
            <th>样本 Sample</th>
            <th>目标字段 Target</th>
            <th>方法 Method</th>
            <th>置信度</th>
            <th>状态</th>
            <th>证据</th>
            <th>审核</th>
          </tr>
        </thead>
        <tbody>
          {mappings.map((mapping) => {
            const draftTarget = draftTargets[mapping.mapping_id] ?? mapping.target_field_id;
            return (
              <tr
                className={mapping.need_review ? "data-table__row--review" : undefined}
                key={mapping.mapping_id}
              >
                <td>
                  <strong>{mapping.source_name}</strong>
                  <small className="field-path">{mapping.source_path}</small>
                </td>
                <td className="sample-cell">
                  {candidateSamples[mapping.candidate_id] ?? "-"}
                </td>
                <td>
                  <select
                    aria-label={`为 ${mapping.source_name} 选择 Target field`}
                    onChange={(event) =>
                      setDraftTargets((current) => ({
                        ...current,
                        [mapping.mapping_id]: event.target.value,
                      }))
                    }
                    value={draftTarget}
                  >
                    {fallbackTargetFields.map((fieldId) => (
                      <option key={fieldId} value={fieldId}>
                        {fieldId}
                      </option>
                    ))}
                  </select>
                </td>
                <td><MethodBadge method={mapping.method} /></td>
                <td><ConfidenceBadge value={mapping.confidence} /></td>
                <td>
                  <StatusBadge
                    label={labelForStatus(mapping)}
                    status={mapping.need_review ? "review_required" : mapping.status}
                  />
                </td>
                <td>
                  <div className="evidence-list">
                    {mapping.evidence.map((item) => (
                      <span key={item}>{item}</span>
                    ))}
                  </div>
                </td>
                <td>
                  <button
                    className="secondary-button"
                    onClick={() => onReview(mapping, draftTarget)}
                    type="button"
                  >
                    <CheckCircle2 aria-hidden="true" size={15} />
                    确认
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
