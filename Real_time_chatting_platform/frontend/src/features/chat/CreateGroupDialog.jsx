import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Alert, Avatar, Button, Field, Input, Spinner } from "../../components/ui";
import UserPicker from "../users/UserPicker";
import { describeApiError } from "../../lib/apiClient";
import { useChatStore } from "../../stores/chatStore";

/**
 * Create a group.
 *
 * Members are optional: the backend takes an empty member_ids and the members
 * panel can fill the group afterwards, so an accidentally-empty group is
 * recoverable rather than a dead end.
 */
export default function CreateGroupDialog({ onClose }) {
  const navigate = useNavigate();
  const createGroup = useChatStore((state) => state.createGroup);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [invitees, setInvitees] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Escape closes, matching every other dialog users have met.
  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const trimmedName = name.trim();
  const canSubmit = trimmedName.length > 0 && !submitting;

  async function handleSubmit(event) {
    event.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError(null);
    try {
      const conversation = await createGroup({
        name: trimmedName,
        description: description.trim(),
        memberIds: invitees.map((u) => u.id),
      });
      onClose();
      navigate(`/c/${conversation.id}`);
    } catch (err) {
      setError(describeApiError(err, "Could not create the group."));
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Create a group"
      onMouseDown={(event) => {
        // Only a click on the backdrop itself closes — not one that started
        // inside the panel and drifted out while selecting text.
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-md rounded-xl border border-edge bg-surface shadow-xl">
        <header className="flex items-center justify-between border-b border-edge px-4 py-3">
          <h2 className="text-sm font-semibold text-white">New group</h2>
          <Button variant="ghost" onClick={onClose} aria-label="Close">
            ✕
          </Button>
        </header>

        <form onSubmit={handleSubmit} className="space-y-4 p-4">
          {error ? <Alert>{error}</Alert> : null}

          <Field label="Name" htmlFor="group-name">
            <Input
              id="group-name"
              value={name}
              maxLength={100}
              autoFocus
              required
              onChange={(event) => setName(event.target.value)}
              placeholder="Design team"
            />
          </Field>

          <Field label="Description" htmlFor="group-description" hint="Optional.">
            <Input
              id="group-description"
              value={description}
              maxLength={500}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="What is this group for?"
            />
          </Field>

          <div className="space-y-2">
            <p className="text-sm text-slate-300">
              Members{" "}
              <span className="text-xs text-slate-500">
                Optional — you can add people later.
              </span>
            </p>

            {invitees.length > 0 ? (
              <ul className="flex flex-wrap gap-1.5">
                {invitees.map((user) => (
                  <li
                    key={user.id}
                    className="flex items-center gap-1.5 rounded-full border border-edge bg-surface-sunken py-1 pl-1 pr-2 text-xs text-slate-200"
                  >
                    <Avatar user={user} size={20} />
                    <span className="max-w-32 truncate">
                      {user.display_name || user.username}
                    </span>
                    <button
                      type="button"
                      onClick={() =>
                        setInvitees((list) => list.filter((u) => u.id !== user.id))
                      }
                      aria-label={`Remove ${user.username}`}
                      className="rounded px-0.5 text-slate-500 transition hover:text-red-300"
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}

            <UserPicker
              placeholder="Add people…"
              excludeIds={invitees.map((u) => u.id)}
              onSelect={(user) => setInvitees((list) => [...list, user])}
            />
          </div>

          <div className="flex justify-end gap-2 border-t border-edge pt-4">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={!canSubmit}>
              {submitting ? <Spinner /> : null}
              Create group
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
