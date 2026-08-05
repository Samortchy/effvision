import { useState } from "react";

import { Button } from "../../components/ui";
import { describeApiError } from "../../lib/apiClient";
import { useChatStore } from "../../stores/chatStore";

export default function MessageComposer({ conversationId, onTyping, onSent }) {
  const sendMessage = useChatStore((state) => state.sendMessage);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState(null);
  const [sending, setSending] = useState(false);

  // Mirrors MessageRequest.content on the server (1–4000). Enforced here too so
  // an over-long paste is caught before it costs a round trip and a 422.
  const MAX_LENGTH = 4000;
  const trimmed = draft.trim();
  const tooLong = draft.length > MAX_LENGTH;
  const canSend = trimmed.length > 0 && !tooLong && !sending;

  async function handleSubmit(event) {
    event.preventDefault();
    if (!canSend) return;

    setSending(true);
    setError(null);
    // Cleared optimistically so the box is ready for the next message, and
    // restored if the send fails rather than silently losing what was typed.
    setDraft("");
    try {
      await sendMessage(conversationId, trimmed);
      // The message itself ends the typing state — no need to wait for the
      // idle timer to fire a typing_stop.
      onSent?.();
    } catch (err) {
      setDraft(trimmed);
      setError(describeApiError(err, "Could not send that message."));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="border-t border-edge px-4 py-3">
      <form onSubmit={handleSubmit} className="flex items-end gap-2">
        <textarea
          rows={1}
          value={draft}
          onChange={(event) => {
            setDraft(event.target.value);
            // Throttled inside the hook: one typing_start, then a single
            // typing_stop once the user goes quiet — not a frame per keystroke.
            onTyping?.();
          }}
          onKeyDown={(event) => {
            // Enter sends; Shift+Enter inserts a newline.
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              handleSubmit(event);
            }
          }}
          placeholder="Write a message…"
          aria-label="Message"
          className="max-h-40 min-h-[42px] flex-1 resize-y rounded-lg border border-edge bg-surface-sunken px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:border-accent focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
        />
        <Button type="submit" disabled={!canSend}>
          Send
        </Button>
      </form>

      {tooLong ? (
        <p className="mt-2 text-xs text-amber-300">
          {draft.length.toLocaleString()} / {MAX_LENGTH.toLocaleString()} characters — too long to send.
        </p>
      ) : null}
      {error ? <p className="mt-2 text-xs text-red-300">{error}</p> : null}
    </div>
  );
}
