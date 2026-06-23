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
    return "Needs review";
  }
  if (mapping.status === "confirmed") {
    return "Confirmed";
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
        <strong>No mappings yet.</strong>
        <span>Generate candidates and run mapping to populate review rows.</span>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Source</th>
            <th>Sample</th>
            <th>Target</th>
            <th>Method</th>
            <th>Confidence</th>
            <th>Status</th>
            <th>Evidence</th>
            <th>Review</th>
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
                    aria-label={`Target field for ${mapping.source_name}`}
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
                    Confirm
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
