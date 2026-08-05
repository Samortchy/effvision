import { Avatar } from "../../components/ui";
import { shortId } from "../../lib/formatters";
import { useChatStore } from "../../stores/chatStore";

/**
 * Typing bubble — an incoming message that has not been written yet.
 *
 * Deliberately shaped like a message row (avatar in the same 36px gutter,
 * bubble on the same left edge) so it reads as the next thing arriving in the
 * thread rather than as a status line about the thread.
 *
 * Renders nothing at all when nobody is typing, so the message list does not
 * shift by a row every time someone starts and stops.
 */
export default function TypingIndicator({ userIds }) {
  const userCache = useChatStore((state) => state.userCache);

  if (!userIds || userIds.length === 0) return null;

  // The typing frame carries a user_id only. Anyone this browser has seen
  // resolves to a name; anyone else degrades to a short id rather than vanishing.
  const people = userIds.map((id) => ({
    id,
    user: userCache[id],
    label: userCache[id]?.display_name || userCache[id]?.username || shortId(id),
  }));

  const [first] = people;
  const label =
    people.length === 1
      ? `${first.label} is typing`
      : people.length === 2
        ? `${first.label} and ${people[1].label} are typing`
        : `${first.label} and ${people.length - 1} others are typing`;

  return (
    <div className="flex items-end gap-2.5 px-4 pb-2">
      <div className="w-9 shrink-0">
        {people.length === 1 ? (
          <Avatar user={first.user} size={36} />
        ) : (
          // Overlapped avatars for a group, capped at three so a busy room
          // cannot push the bubble off its own line.
          <div className="flex -space-x-2">
            {people.slice(0, 3).map((p) => (
              <span key={p.id} className="ring-2 ring-surface rounded-full">
                <Avatar user={p.user} size={24} />
              </span>
            ))}
          </div>
        )}
      </div>

      {/* aria-label carries the names; the dots are decorative, so they are
          hidden from assistive tech rather than read out as punctuation. */}
      <div
        role="status"
        aria-live="polite"
        aria-label={label}
        title={label}
        className="flex items-center gap-1 rounded-2xl rounded-bl-md border border-edge bg-surface-raised px-3 py-2.5"
      >
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            aria-hidden="true"
            className="typing-dot block h-1.5 w-1.5 rounded-full bg-slate-400"
            style={{ animationDelay: `${i * 0.16}s` }}
          />
        ))}
      </div>
    </div>
  );
}
