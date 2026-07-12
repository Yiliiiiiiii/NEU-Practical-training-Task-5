export type UirDocumentInput = {
  doc_id: string;
  blocks: unknown[];
  [key: string]: unknown;
};

export type UirValidationResult =
  | { valid: true; document: UirDocumentInput }
  | { valid: false; error: string };

export function validateUirText(text: string): UirValidationResult {
  let parsed: unknown;

  try {
    parsed = JSON.parse(text);
  } catch {
    return { valid: false, error: "JSON 格式无效。" };
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { valid: false, error: "UIR 必须是 JSON 对象。" };
  }

  const document = parsed as Record<string, unknown>;
  if (typeof document.doc_id !== "string" || !document.doc_id.trim()) {
    return { valid: false, error: "UIR 必须包含非空 doc_id。" };
  }
  if (!Array.isArray(document.blocks)) {
    return { valid: false, error: "UIR 必须包含 blocks 数组。" };
  }

  return { valid: true, document: document as UirDocumentInput };
}
