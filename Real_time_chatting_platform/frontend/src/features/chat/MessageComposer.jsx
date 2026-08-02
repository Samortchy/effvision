import { useState } from "react";

import { Button } from "../../components/ui";
import { useChatStore } from "../../stores/chatStore";

/**
 * Composer for step 7 (real-time send).
 *
 * ⚠️ Disabled on purpose. There is no endpoint to send a message: messages.py
 * has only DELETE and search, no api/websocket/ package exists, and the
 * broadcaster imports a connection_manager module that was never written. The
 * input is left visible but inert so the layout is finished and the reason is
 * obvious — see chatStore.sendMessage for the single call site to enable.
 */
export default function MessageComposer({ conversationId }) {
  const sendMessage = useChatStore((state) => state.sendMessage);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState(null);

  const canSend = false; // flip when the backend send path exists

  async function handleSubmit(event) {
    event.preventDefault();
    if (!draft.trim()) return;
    try {
      await sendMessage(conversationId, draft.trim());
      setDraft("");
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="border-t border-edge px-4 py-3">
      <div className="mb-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
        <strong className="font-semibold">Sending is not wired up yet.</strong>{" "}
        The backend has no send-message route and no WebSocket layer — both are
        still in progress. History, search and delete all work.
      </div>

      <form onSubmit={handleSubmit} className="flex items-end gap-2">
        <textarea
          rows={1}
          value={draft}
          disabled={!canSend}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              handleSubmit(event);
            }
          }}
          placeholder="Sending is unavailable until the backend ships it"
          aria-label="Message"
          className="max-h-40 min-h-[42px] flex-1 resize-y rounded-lg border border-edge bg-surface-sunken px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:border-accent focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
        />
        <Button type="submit" disabled={!canSend || !draft.trim()}>
          Send
        </Button>
      </form>

      {error ? <p className="mt-2 text-xs text-red-300">{error}</p> : null}
    </div>
  );
}
