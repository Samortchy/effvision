import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Avatar, Input, Spinner } from "../../components/ui";
import { describeApiError } from "../../lib/apiClient";
import { searchUsers } from "./api";
import { useAuthStore } from "../../stores/authStore";
import { useChatStore } from "../../stores/chatStore";

const DEBOUNCE_MS = 250;

export default function UserSearch() {
  const navigate = useNavigate();
  const currentUser = useAuthStore((state) => state.user);
  const openPrivateConversation = useChatStore((state) => state.openPrivateConversation);
  const cacheUsers = useChatStore((state) => state.cacheUsers);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [starting, setStarting] = useState(null);

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
        // Cache them: messages carry only sender_id, so this is how names get
        // resolved later.
        cacheUsers(users);
        setResults(users.filter((u) => u.id !== currentUser?.id));
        setError(null);
      } catch (err) {
        if (requestId !== requestIdRef.current) return;
        setError(describeApiError(err, "Search failed."));
      } finally {
        if (requestId === requestIdRef.current) setLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [query, currentUser?.id, cacheUsers]);

  async function handleSelect(user) {
    setStarting(user.id);
    try {
      const conversation = await openPrivateConversation(user);
      setQuery("");
      setResults([]);
      navigate(`/c/${conversation.id}`);
    } catch (err) {
      setError(describeApiError(err, "Could not start that conversation."));
    } finally {
      setStarting(null);
    }
  }

  return (
    <div className="space-y-2">
      <div className="relative">
        <Input
          type="search"
          placeholder="Search people…"
          aria-label="Search people"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {loading ? (
          <Spinner className="absolute right-3 top-1/2 -translate-y-1/2" />
        ) : null}
      </div>

      {error ? <p className="text-xs text-red-300">{error}</p> : null}

      {results.length > 0 ? (
        <ul className="max-h-64 space-y-0.5 overflow-y-auto rounded-lg border border-edge bg-surface p-1">
          {results.map((user) => (
            <li key={user.id}>
              <button
                type="button"
                onClick={() => handleSelect(user)}
                disabled={starting === user.id}
                className="flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left text-sm text-slate-200 transition hover:bg-surface-raised disabled:opacity-60"
              >
                <Avatar user={user} size={28} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate">
                    {user.display_name || user.username}
                  </span>
                  <span className="block truncate text-xs text-slate-500">
                    @{user.username}
                  </span>
                </span>
                {starting === user.id ? <Spinner /> : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {query.trim() && !loading && results.length === 0 && !error ? (
        <p className="text-xs text-slate-500">No users matched.</p>
      ) : null}
    </div>
  );
}
