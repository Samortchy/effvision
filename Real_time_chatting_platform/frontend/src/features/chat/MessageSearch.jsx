import { useState } from "react";

import { Button, Input, Spinner } from "../../components/ui";
import { describeApiError } from "../../lib/apiClient";
import { formatDay, formatTime } from "../../lib/formatters";
import { searchMessages } from "./api";

/**
 * Full-text search within a conversation.
 *
 * Note this endpoint is offset-paginated (limit/offset), unlike the history
 * endpoint's `before` cursor — they are genuinely different pagination schemes
 * on the backend, so this "Load more" is a page walk rather than a cursor walk.
 */
export default function MessageSearch({ conversationId }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const LIMIT = 20;

  async function runSearch(nextOffset = 0) {
    const trimmed = query.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);
    try {
      const page = await searchMessages(conversationId, {
        q: trimmed,
        limit: LIMIT,
        offset: nextOffset,
      });
      setResults((prev) => (nextOffset === 0 ? page : [...(prev ?? []), ...page]));
      setOffset(nextOffset + page.length);
    } catch (err) {
      setError(describeApiError(err, "Search failed."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="border-b border-edge bg-surface-sunken px-4 py-3">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          runSearch(0);
        }}
        className="flex gap-2"
      >
        <Input
          type="search"
          placeholder="Search this conversation…"
          aria-label="Search messages"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <Button type="submit" disabled={loading || !query.trim()}>
          {loading ? <Spinner /> : "Search"}
        </Button>
      </form>

      {error ? <p className="mt-2 text-xs text-red-300">{error}</p> : null}

      {results ? (
        <div className="mt-3 max-h-56 overflow-y-auto">
          {results.length === 0 ? (
            <p className="text-xs text-slate-500">No matches.</p>
          ) : (
            <ul className="space-y-1.5">
              {results.map((message) => (
                <li
                  key={message.id}
                  className="rounded-md border border-edge bg-surface px-2.5 py-1.5"
                >
                  <p className="text-xs text-slate-500">
                    {formatDay(message.created_at)} · {formatTime(message.created_at)}
                  </p>
                  <p className="break-words text-sm text-slate-200">
                    {message.content}
                  </p>
                </li>
              ))}
            </ul>
          )}

          {results.length > 0 && results.length % LIMIT === 0 ? (
            <Button
              variant="ghost"
              className="mt-2 w-full"
              disabled={loading}
              onClick={() => runSearch(offset)}
            >
              Load more
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
