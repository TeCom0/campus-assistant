import { useRef, type FormEvent, type KeyboardEvent } from "react";
import { SendIcon } from "./icons";

const MAX_HEIGHT_PX = 160;

export function Composer({
  value,
  onChange,
  onSubmit,
  busy,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  busy: boolean;
  placeholder: string;
}) {
  const textarea = useRef<HTMLTextAreaElement>(null);

  // Grows with its text up to MAX_HEIGHT_PX, then scrolls.
  function resize() {
    const el = textarea.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`;
  }

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (busy || !value.trim()) return;
    onSubmit();
    requestAnimationFrame(resize);
  }

  // Enter sends, Shift+Enter adds a line; not while an IME is composing a word.
  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  }

  const canSend = !busy && value.trim().length > 0;
  return (
    <div className="composer-dock">
      <form className="composer" onSubmit={submit}>
        <label htmlFor="question" className="visually-hidden">
          Your question
        </label>
        <textarea
          id="question"
          ref={textarea}
          rows={1}
          value={value}
          placeholder={placeholder}
          onChange={(e) => {
            onChange(e.target.value);
            resize();
          }}
          onKeyDown={onKeyDown}
        />
        <button type="submit" className="send" disabled={!canSend} aria-label="Send question">
          <SendIcon />
        </button>
      </form>
      <p className="disclaimer">
        Answers are based on the Academic Catalog 2024–2025. Unofficial student project, not an
        AUI service. Answers can be wrong: check important details with the Registrar.
      </p>
    </div>
  );
}
