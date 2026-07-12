import { describe, expect, it } from "vitest";

import { validateUirText } from "./uirValidation";

describe("validateUirText", () => {
  it("requires a JSON object with a nonempty doc_id and a blocks array", () => {
    expect(validateUirText("not json").valid).toBe(false);
    expect(validateUirText('{"doc_id":"","blocks":[]}').valid).toBe(false);
    expect(validateUirText('{"doc_id":"doc-1","blocks":{}}').valid).toBe(false);

    expect(
      validateUirText('{"doc_id":"doc-1","blocks":[{"block_id":"b-1","text":"正文"}]}')
    ).toMatchObject({ valid: true, document: { doc_id: "doc-1" } });
  });
});
