import { FileUp } from "lucide-react";
import type { ChangeEvent } from "react";

interface JsonWorkbenchProps {
  id: string;
  title: string;
  description: string;
  value: string;
  error: string | null;
  onChange: (value: string) => void;
}

export function JsonWorkbench({
  id,
  title,
  description,
  value,
  error,
  onChange,
}: JsonWorkbenchProps) {
  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    onChange(await file.text());
    event.target.value = "";
  }

  return (
    <section className="json-editor-panel" aria-labelledby={`${id}-title`}>
      <div className="json-editor-panel__header">
        <div>
          <h3 id={`${id}-title`}>{title}</h3>
          <p>{description}</p>
        </div>
        <label className="file-button">
          <FileUp aria-hidden="true" size={15} />
          File
          <input accept="application/json,.json" onChange={handleFileChange} type="file" />
        </label>
      </div>
      <textarea
        aria-invalid={Boolean(error)}
        aria-label={title}
        className="json-editor-panel__textarea"
        onChange={(event) => onChange(event.target.value)}
        spellCheck={false}
        value={value}
      />
      <div className={error ? "json-status json-status--error" : "json-status"}>
        {error ?? "Valid JSON object"}
      </div>
    </section>
  );
}
