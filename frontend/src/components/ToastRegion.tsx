import type { ToastMessage } from "../appTypes";

interface ToastRegionProps {
  messages: ToastMessage[];
}

export function ToastRegion({ messages }: ToastRegionProps) {
  return (
    <section className="toast-region" aria-live="polite" aria-label="Status messages">
      {messages.map((message) => (
        <article className={`toast toast--${message.tone}`} key={message.id}>
          <strong>{message.title}</strong>
          {message.detail ? <span>{message.detail}</span> : null}
        </article>
      ))}
    </section>
  );
}
