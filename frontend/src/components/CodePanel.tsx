import { Check, Copy } from "lucide-react";
import { useState } from "react";

interface CodePanelProps {
  title: string;
  value: unknown | null;
  emptyMessage?: string;
}

export function CodePanel({
  title,
  value,
  emptyMessage = "No data loaded yet.",
}: CodePanelProps) {
  const [didCopy, setDidCopy] = useState(false);
  const formatted = value === null ? "" : JSON.stringify(value, null, 2);

  async function handleCopy() {
    if (!formatted || !navigator.clipboard) {
      return;
    }
    await navigator.clipboard.writeText(formatted);
    setDidCopy(true);
    window.setTimeout(() => setDidCopy(false), 1400);
  }

  return (
    <section className="code-panel" aria-label={title}>
      <div className="code-panel__bar">
        <strong>{title}</strong>
        <button
          aria-label="Copy panel JSON"
          className="icon-button code-panel__copy"
          disabled={!formatted}
          onClick={() => void handleCopy()}
          title={`Copy ${title}`}
          type="button"
        >
          {didCopy ? <Check aria-hidden="true" size={14} /> : <Copy aria-hidden="true" size={14} />}
        </button>
      </div>
      {formatted ? (
        <pre tabIndex={0}>
          <code>{formatted}</code>
        </pre>
      ) : (
        <div className="code-panel__empty">{emptyMessage}</div>
      )}
    </section>
  );
}
