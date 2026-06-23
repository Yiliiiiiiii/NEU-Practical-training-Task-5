import { X } from "lucide-react";

import type { ToastMessage } from "../appTypes";

interface ToastRegionProps {
  messages: ToastMessage[];
  onDismiss: (id: string) => void;
}

export function ToastRegion({ messages, onDismiss }: ToastRegionProps) {
  return (
    <section className="toast-region" aria-live="polite" aria-label="状态消息">
      {messages.map((message) => (
        <article className={`toast toast--${message.tone}`} key={message.id}>
          <div className="toast__content">
            <strong>{message.title}</strong>
            {message.detail ? <span>{message.detail}</span> : null}
          </div>
          <button
            aria-label={`关闭 ${message.title}`}
            className="toast__dismiss"
            onClick={() => onDismiss(message.id)}
            title="关闭消息"
            type="button"
          >
            <X aria-hidden="true" size={15} />
          </button>
        </article>
      ))}
    </section>
  );
}
