# Effvision Chat — Frontend

React + Vite + Tailwind CSS 4, Zustand for global state, react-router-dom for
routing, axios for REST and native `EventSource` for the notification stream.

```bash
cp .env.example .env      # point VITE_API_BASE_URL at the FastAPI server
npm install
npm run dev               # http://localhost:5173
```

## Layout

```
src/
  lib/           apiClient (axios + refresh interceptor), session (token holder),
                 realtime (WebSocket wrapper, inert), formatters
  stores/        authStore, chatStore, notificationStore
  components/    AppLayout, Sidebar, ui/ primitives
  features/
    auth/        LoginPage, RegisterPage, ProtectedRoute, api
    users/       UserSearch, api
    chat/        ChatPanel, MessageList, MessageComposer, MessageSearch,
                 MembersPanel, api
    notifications/ NotificationBell, ToastHost, useNotificationStream
```

Global state is split three ways and holds only what is genuinely shared:
session/user, conversations + message threads, and the notification feed.
Form fields, popover open/closed, search boxes and panel toggles are all
`useState` inside their components.

## Auth flow

- **Access token: memory only** (`lib/session.js`). It never touches
  localStorage, so it is gone on reload by design.
- **Refresh token: localStorage.** The backend returns it as JSON rather than
  setting an httpOnly cookie, so there is nowhere better to put it. On boot,
  `authStore.bootstrap()` trades it for a fresh pair and calls `GET /users/me`.
- **401 handling** (`lib/apiClient.js`): one refresh, one retry, then sign out.
  The refresh call is a *single shared promise* — the backend rotates refresh
  tokens, so two concurrent 401s each firing their own refresh would race, and
  the second would present a token the first had already consumed and
  invalidated. Collapsing them means N stalled requests resume on one rotation.

## Backend gaps this frontend is built around

Verified by reading the backend on 2026-07-30. Each is marked in the code at the
point where it bites.

| # | Gap | Effect here |
|---|-----|-------------|
| 1 | **No `POST /auth/login`.** `api/routes/auth.py` has only register/refresh/logout; `LoginRequest{identifier, password}` exists in the DTOs but is imported nowhere, there is no login use case, and `verify_password` is never called. | Login UI is built to the contract the unused DTO implies (`features/auth/api.js`). It returns 404 until the route ships, and the UI says exactly that instead of a generic error. **Nothing downstream can be exercised end-to-end until this exists.** |
| 2 | **The backend does not currently import.** `api/dependencies/auth.py:74` calls `Query(...)` but the module never imports `Query` from fastapi — a `NameError` at import time, reached through `main.py` → notifications router. | The API cannot start at all, so none of this has been run against a live server. |
| 3 | **No CORS middleware.** `main.py` adds only `LoggingMiddleware`. | Every browser request from `:5173` will fail until `CORSMiddleware` is added with the dev origin allowed. `describeApiError` calls this out by name on a network error. |
| 4 | **No "list my conversations" endpoint.** | The sidebar list is local-only, kept in `chatStore` and persisted to localStorage. A fresh device starts empty and conversations others started with you appear only via a notification. The sidebar states this inline. |
| 5 | **No send-message route and no WebSocket layer.** `messages.py` has only DELETE + search; there is no `api/websocket/` package; `infrastructure/websocket/broadcaster.py` imports a `connection_manager` module that does not exist. | The composer renders but is disabled with the reason shown. `lib/realtime.js` is a written-but-inert wrapper behind `VITE_ENABLE_WEBSOCKET`, with the steps to enable it. |
| 6 | **No endpoint returns conversation members.** `ConversationMemberResponse` is defined but never returned. | `MembersPanel` actions (leave / change role / remove) are wired to the real endpoints and work; the member *list* is drawn from locally known users, and current roles are unknown. One function swap (`chatApi.fetchMembers`) fixes it. |

Also noted while reading, not worked around: `PATCH /users/me` annotates
`current_user` as `UpdateProfileRequest` while depending on `get_current_user`
(`users.py:39`), so it can never receive a request body.

## Pagination

`GET /conversations/{id}/messages` is cursor-based. Confirmed in
`message_repository_sqla.py`: it orders `created_at DESC` and applies `before`
as a strict `<`. So:

- results arrive **newest first** and are reversed for display;
- the cursor for the next older page is the **oldest loaded message's**
  `created_at`, and the strict `<` means no duplicate row at the seam;
- a full page implies more history, a short page is the end.

`MessageList` captures `scrollHeight - scrollTop` before a prepend and restores
it in a `useLayoutEffect`, so loading older messages never yanks the viewport.

Message *search* is different — `GET /messages/{id}/search` is `limit`/`offset`
paginated, so that panel walks pages rather than cursors.

## Notification stream

`useNotificationStream` follows the backend's two quirks:

- the access token goes in `?token=`, because `EventSource` cannot set headers
  (`get_current_user_sse` accepts it there and prefers the header when present);
- reconnection is left to the browser. The server emits an ISO-timestamp `id`
  per event and parses the replayed `Last-Event-ID` as a resume cursor, so drops
  recover on their own and there is no retry code here.

The one exception: access tokens expire after 15 minutes, and a stream that dies
on an expired token gets a **401 response**, which per spec fails the connection
permanently — `readyState` goes to `CLOSED` and the browser never retries. That
single case triggers a token refresh and reopen, which is the gap `EventSource`
cannot cover itself.

Events are dispatched with `addEventListener("notification")` and
`addEventListener("system_announcement")` — the server sets the SSE `event:`
field from `event_category`, so a bare `onmessage` would never fire. Only real
notifications are marked read over the API; system announcement ids come from a
different table and would 404, so they are acknowledged locally.

## Verification status

`npm run build` compiles and the dev server serves. **None of it has been
exercised against a running backend** — the API cannot start (gap 2) and has no
login route (gap 1), so there is no way to obtain a token yet.
