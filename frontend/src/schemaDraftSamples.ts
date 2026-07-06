export function parseSchemaDraftSamples(text: string): Array<Record<string, any>> {
  const parsed = JSON.parse(text);
  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error("Sample JSON must be a non-empty array.");
  }
  if (parsed.some((item) => !item || typeof item !== "object" || Array.isArray(item))) {
    throw new Error("Every sample must be a UIR object.");
  }
  return parsed as Array<Record<string, any>>;
}
