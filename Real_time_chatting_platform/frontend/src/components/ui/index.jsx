/** Small shared primitives. Local UI state only — nothing here touches a store. */

export function Button({
  variant = "primary",
  className = "",
  type = "button",
  ...props
}) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70";
  const variants = {
    primary: "bg-accent text-slate-950 hover:brightness-110",
    ghost: "text-slate-300 hover:bg-surface-raised hover:text-white",
    outline: "border border-edge text-slate-200 hover:bg-surface-raised",
    danger: "bg-red-500/90 text-white hover:bg-red-500",
  };
  return (
    <button type={type} className={`${base} ${variants[variant]} ${className}`} {...props} />
  );
}

export function Input({ className = "", ...props }) {
  return (
    <input
      className={`w-full rounded-lg border border-edge bg-surface-sunken px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent ${className}`}
      {...props}
    />
  );
}

export function Field({ label, htmlFor, children, hint }) {
  return (
    <label className="block space-y-1.5" htmlFor={htmlFor}>
      <span className="text-xs font-medium uppercase tracking-wide text-slate-400">
        {label}
      </span>
      {children}
      {hint ? <span className="block text-xs text-slate-500">{hint}</span> : null}
    </label>
  );
}

export function Avatar({ user, size = 36 }) {
  const label = user?.display_name || user?.username || "?";
  const statusColor = {
    online: "bg-emerald-400",
    away: "bg-amber-400",
    offline: "bg-slate-500",
  }[user?.status ?? "offline"];

  return (
    <span className="relative inline-flex shrink-0" style={{ width: size, height: size }}>
      {user?.avatar_url ? (
        <img
          src={user.avatar_url}
          alt=""
          className="h-full w-full rounded-full object-cover"
        />
      ) : (
        <span
          className="flex h-full w-full items-center justify-center rounded-full bg-surface-raised text-sm font-semibold text-slate-300"
          aria-hidden="true"
        >
          {label.charAt(0).toUpperCase()}
        </span>
      )}
      {user?.status ? (
        <span
          className={`absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-surface ${statusColor}`}
        />
      ) : null}
    </span>
  );
}

export function Spinner({ className = "" }) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-500 border-t-transparent ${className}`}
    />
  );
}

export function Alert({ tone = "error", children, className = "" }) {
  const tones = {
    error: "border-red-500/40 bg-red-500/10 text-red-200",
    warning: "border-amber-500/40 bg-amber-500/10 text-amber-100",
    info: "border-edge bg-surface-raised text-slate-300",
  };
  return (
    <div
      role={tone === "error" ? "alert" : undefined}
      className={`rounded-lg border px-3 py-2 text-sm ${tones[tone]} ${className}`}
    >
      {children}
    </div>
  );
}

export function EmptyState({ title, children }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center">
      <p className="text-sm font-medium text-slate-300">{title}</p>
      {children ? <p className="max-w-sm text-sm text-slate-500">{children}</p> : null}
    </div>
  );
}
