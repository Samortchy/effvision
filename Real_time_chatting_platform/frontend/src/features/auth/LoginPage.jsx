import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { Alert, Button, Field, Input, Spinner } from "../../components/ui";
import { describeApiError } from "../../lib/apiClient";
import { useAuthStore } from "../../stores/authStore";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const login = useAuthStore((state) => state.login);
  const status = useAuthStore((state) => state.status);
  const sessionError = useAuthStore((state) => state.error);

  // Local-only form state — nothing here belongs in a store.
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  if (status === "authenticated") return <Navigate to="/" replace />;

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login({ identifier, password });
      navigate(location.state?.from ?? "/", { replace: true });
    } catch (err) {
      // 401 is the only expected failure: a deliberately generic message that
      // does not say whether it was the identifier or the password.
      setError(describeApiError(err, "Could not sign in."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm space-y-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold text-white">Sign in</h1>
          <p className="text-sm text-slate-400">Welcome back to Effvision Chat.</p>
        </header>

        {sessionError ? <Alert tone="info">{sessionError}</Alert> : null}
        {error ? <Alert>{error}</Alert> : null}

        <form onSubmit={handleSubmit} className="space-y-4">
          <Field
            label="Email or username"
            htmlFor="identifier"
            hint="The backend takes a single `identifier` for either."
          >
            <Input
              id="identifier"
              name="identifier"
              autoComplete="username"
              required
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
            />
          </Field>

          <Field label="Password" htmlFor="password">
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>

          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? <Spinner /> : null}
            Sign in
          </Button>
        </form>

        <p className="text-sm text-slate-400">
          No account?{" "}
          <Link to="/register" className="text-accent hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
