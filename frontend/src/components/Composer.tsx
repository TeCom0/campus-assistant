import { useEffect, useRef, type FormEvent, type KeyboardEvent } from "react";
import { limitMessages } from "../limitMessages";
import { privacyNotice } from "../privacyNotice";
import { charCount, COUNTER_FROM_CHARS, MAX_QUESTION_CHARS } from "../requestLimits";
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
  // After trimming, as the server counts it. Going over blocks sending but keeps
  // the text: a maxLength attribute would silently cut what was pasted.
  const count = charCount(value.trim());
  const tooLong = count > MAX_QUESTION_CHARS;
  const canSend = !busy && count > 0 && !tooLong;

  // Grows with its text up to MAX_HEIGHT_PX, then scrolls. On every change of the
  // value, whoever made it: typing, sending, or a refused question coming back.
  useEffect(() => {
    const el = textarea.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`;
  }, [value]);

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!canSend) return;
    onSubmit();
  }

  // Enter sends, Shift+Enter adds a line; not while an IME is composing a word.
  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  }

  const notice = privacyNotice(navigator.language);
  const limits = limitMessages(navigator.language);
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
          aria-invalid={tooLong}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <button type="submit" className="send" disabled={!canSend} aria-label="Send question">
          <SendIcon />
        </button>
      </form>
      {count >= COUNTER_FROM_CHARS && (
        <p className={tooLong ? "composer-count over" : "composer-count"} lang={limits.language} role="status">
          {limits.counter(count)}
          {tooLong && ` · ${limits.tooLong}`}
        </p>
      )}
      <p className="disclaimer" lang={notice.language}>
        {notice.text}
      </p>
      <p className="disclaimer">
        Answers are based on the Academic Catalog 2024–2025. Unofficial student project, not an
        AUI service. Answers can be wrong: check important details with the Registrar.
      </p>
    </div>
  );
}
