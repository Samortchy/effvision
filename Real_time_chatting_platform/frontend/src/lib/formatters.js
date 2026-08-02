const timeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: "2-digit",
  minute: "2-digit",
});

const dayFormatter = new Intl.DateTimeFormat(undefined, {
  weekday: "short",
  month: "short",
  day: "numeric",
});

export function formatTime(iso) {
  if (!iso) return "";
  return timeFormatter.format(new Date(iso));
}

export function formatDay(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  const today = new Date();
  const isToday = date.toDateString() === today.toDateString();
  return isToday ? "Today" : dayFormatter.format(date);
}

export function formatRelative(iso) {
  if (!iso) return "";
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return dayFormatter.format(new Date(iso));
}

/** Title for a conversation row. Private conversations have no server-side name. */
export function conversationTitle(conversation) {
  if (!conversation) return "Conversation";
  if (conversation.name) return conversation.name;
  if (conversation.peer) {
    return conversation.peer.display_name || conversation.peer.username;
  }
  if (conversation.type === "public") return "Public room";
  return `Conversation ${conversation.id.slice(0, 8)}`;
}

/** Fallback label for a sender we have never seen in a search result. */
export function shortId(id) {
  return id ? `${id.slice(0, 8)}…` : "unknown";
}
