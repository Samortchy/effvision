import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Alert, Avatar, Button, Spinner } from "../../components/ui";
import UserPicker from "../users/UserPicker";
import { describeApiError } from "../../lib/apiClient";
import { useChatStore } from "../../stores/chatStore";
import { useFriendStore } from "../../stores/friendStore";

/**
 * Friends, pending requests, and the search box for sending new ones.
 *
 * A dialog rather than a route: it is a side errand from whatever conversation
 * you are in, and routing to it would throw away the open chat.
 */
export default function FriendsPanel({ onClose }) {
  const navigate = useNavigate();
  const { friends, incoming, outgoing, loading, load, sendRequest, accept, decline, remove } =
    useFriendStore();
  const openPrivateConversation = useChatStore((state) => state.openPrivateConversation);

  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  useEffect(() => {
    load().catch(() => {
      /* surfaced through the store's error state */
    });
  }, [load]);

  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  async function run(id, action, successMessage) {
    setBusyId(id);
    setError(null);
    setNotice(null);
    try {
      await action();
      if (successMessage) setNotice(successMessage);
    } catch (err) {
      // 409 carries the useful part: already friends / already asked / they
      // asked you first. describeApiError surfaces the server's own wording.
      setError(describeApiError(err, "That did not work."));
    } finally {
      setBusyId(null);
    }
  }

  async function messageFriend(user) {
    const conversation = await openPrivateConversation(user);
    onClose();
    navigate(`/c/${conversation.id}`);
  }

  // Everyone already connected or mid-negotiation — hidden from the search box
  // so you cannot send a request that is guaranteed to 409.
  const excludeIds = [
    ...friends.map((u) => u.id),
    ...incoming.map((r) => r.user.id),
    ...outgoing.map((r) => r.user.id),
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Friends"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="flex max-h-[80vh] w-full max-w-md flex-col rounded-xl border border-edge bg-surface shadow-xl">
        <header className="flex items-center justify-between border-b border-edge px-4 py-3">
          <h2 className="text-sm font-semibold text-white">Friends</h2>
          <Button variant="ghost" onClick={onClose} aria-label="Close">
            ✕
          </Button>
        </header>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
          {error ? <Alert>{error}</Alert> : null}
          {notice ? <Alert tone="info">{notice}</Alert> : null}

          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Add a friend
            </p>
            <UserPicker
              placeholder="Search people…"
              excludeIds={excludeIds}
              onSelect={(user) =>
                run(
                  user.id,
                  () => sendRequest(user.id),
                  `Request sent to ${user.display_name || user.username}.`,
                )
              }
            />
          </div>

          {loading && friends.length === 0 && incoming.length === 0 ? (
            <div className="flex justify-center py-4">
              <Spinner className="h-5 w-5" />
            </div>
          ) : null}

          {incoming.length > 0 ? (
            <section className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Requests received ({incoming.length})
              </p>
              <ul className="space-y-2">
                {incoming.map((request) => (
                  <li
                    key={request.id}
                    className="flex items-center gap-2.5 rounded-lg border border-edge bg-surface-sunken p-2.5"
                  >
                    <Avatar user={request.user} size={30} />
                    <span className="min-w-0 flex-1 truncate text-sm text-slate-100">
                      {request.user.display_name || request.user.username}
                      <span className="ml-1 text-xs text-slate-500">
                        @{request.user.username}
                      </span>
                    </span>
                    {busyId === request.id ? (
                      <Spinner />
                    ) : (
                      <>
                        <Button
                          className="px-2 py-1 text-xs"
                          onClick={() =>
                            run(request.id, () => accept(request.id), "Friend added.")
                          }
                        >
                          Accept
                        </Button>
                        <Button
                          variant="ghost"
                          className="px-2 py-1 text-xs"
                          onClick={() => run(request.id, () => decline(request.id))}
                        >
                          Decline
                        </Button>
                      </>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {outgoing.length > 0 ? (
            <section className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Requests sent ({outgoing.length})
              </p>
              <ul className="space-y-1.5">
                {outgoing.map((request) => (
                  <li
                    key={request.id}
                    className="flex items-center gap-2.5 rounded-lg border border-edge/60 px-2.5 py-2"
                  >
                    <Avatar user={request.user} size={26} />
                    <span className="min-w-0 flex-1 truncate text-sm text-slate-300">
                      {request.user.display_name || request.user.username}
                    </span>
                    <span className="text-xs text-slate-500">Pending</span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Friends ({friends.length})
            </p>
            {friends.length === 0 ? (
              <p className="text-sm text-slate-500">
                No friends yet. Search above to send a request.
              </p>
            ) : (
              <ul className="space-y-2">
                {friends.map((friend) => (
                  <li
                    key={friend.id}
                    className="flex items-center gap-2.5 rounded-lg border border-edge bg-surface-sunken p-2.5"
                  >
                    <Avatar user={friend} size={30} />
                    <span className="min-w-0 flex-1 truncate text-sm text-slate-100">
                      {friend.display_name || friend.username}
                      <span className="ml-1 text-xs text-slate-500">@{friend.username}</span>
                    </span>
                    {busyId === friend.id ? (
                      <Spinner />
                    ) : (
                      <>
                        <Button
                          variant="ghost"
                          className="px-2 py-1 text-xs"
                          onClick={() => messageFriend(friend)}
                        >
                          Message
                        </Button>
                        <Button
                          variant="danger"
                          className="px-2 py-1 text-xs"
                          onClick={() =>
                            run(
                              friend.id,
                              () => remove(friend.id),
                              `${friend.display_name || friend.username} removed.`,
                            )
                          }
                        >
                          Remove
                        </Button>
                      </>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
