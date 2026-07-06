type ReviewBatchItem = {
  schema_id: string | null;
  template_id: string | null;
  source_field_name: string | null;
  target_field_id: string | null;
  reason: string | null;
};

export function canBatchApprove(items: ReviewBatchItem[]): boolean {
  if (items.length < 2) {
    return false;
  }
  const scopes = new Set(
    items.map((item) =>
      [
        item.schema_id,
        item.template_id,
        item.source_field_name,
        item.target_field_id
      ].join("|")
    )
  );
  return scopes.size === 1 && items.every((item) => !item.reason?.includes("risk_flags="));
}
