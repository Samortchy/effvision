import { useEffect, useRef, useState } from "react";

import { Avatar, Input, Spinner } from "../../components/ui";
import { describeApiError } from "../../lib/apiClient";
import { searchUsers } from "./api";
import { useAuthStore } from "../../stores/authStore";
import { useChatStore } from "../../stores/chatStore";

const DEBOUNCE_MS = 250;

/**
 * Debounced user search that hands the chosen user back to the caller.
 *
 * Extracted from UserSearch, which navigates to a private conversation on
 * click — the group dialog and the members panel need the same search with a
 * different outcome, and duplicating the debounce plus the stale-response guard
 * in three places is how they drift apart.
 *
 * @param {Function} onSelect      called with the chosen UserSummary
 * @param {string[]} excludeIds    users already chosen/present — hidden from results
 * @param {string}   placeholder
 */
export default function UserPicker({ onSelect, excludeIds = [], placeholder = "Search people…" }) {
  const currentUser = useAuthStore((state) => state.user);
  const cacheUsers = useChatStore((state) => state.cacheUsers);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Ignores responses that come back after a newer keystroke.
  const requestIdRef = useRef(0);

  useEffect(() => {
    const trimmed = query.trim();
    // The endpoint requires 1–50 chars and 422s on an empty q.
    if (!trimmed) {
      setResults([]);
      setError(null);
      setLoading(false);
      return undefined;
    }

    const requestId = ++requestIdRef.current;
    setLoading(true);

    const timer = setTimeout(async () => {
      try {
        const users = await searchUsers({ q: trimmed.slice(0, 50), limit: 10 });
        if (requestId !== requestIdRef.current) return;
        // Messages carry only sender_id, so anyone we surface here is worth
        // remembering for name resolution later.
        cacheUsers(users);
        setResults(users);
        setError(null);
      } catch (err) {
        if (requestId !== requestIdRef.current) return;
        setError(describeApiError(err, "Search failed."));
      } finally {
        if (requestId === requestIdRef.current) setLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [query, cacheUsers]);

  const hidden = new Set([currentUser?.id, ...excludeIds].filter(Boolean));
  const visible = results.filter((u) => !hidden.has(u.id));

  return (
    <div className="space-y-2">
      <div className="relative">
        <Input
          type="search"
          placeholder={placeholder}
          aria-label={placeholder}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {loading ? (
          <Spinner className="absolute right-3 top-1/2 -translate-y-1/2" />
        ) : null}
      </div>

      {error ? <p className="text-xs text-red-300">{error}</p> : null}

      {visible.length > 0 ? (
        <ul className="max-h-48 space-y-0.5 overflow-y-auto rounded-lg border border-edge bg-surface p-1">
          {visible.map((user) => (
            <li key={user.id}>
              <button
                type="button"
                onClick={() => {
                  onSelect(user);
                  setQuery("");
                  setResults([]);
                }}
                className="flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left text-sm text-slate-200 transition hover:bg-surface-raised"
              >
                <Avatar user={user} size={26} />
                <span className="min-w-0 flex-1 truncate">
                  {user.display_name || user.username}
                  <span className="ml-1 text-xs text-slate-500">@{user.username}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {query.trim() && !loading && visible.length === 0 && !error ? (
        <p className="text-xs text-slate-500">No users matched.</p>
      ) : null}
    </div>
  );
}
