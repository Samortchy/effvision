import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { Alert, Button, Field, Input, Spinner } from "../../components/ui";
import { describeApiError } from "../../lib/apiClient";
import { registerRequest } from "./api";
import { useAuthStore } from "../../stores/authStore";

export default function RegisterPage() {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const status = useAuthStore((state) => state.status);

  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  if (status === "authenticated") return <Navigate to="/" replace />;

  const update = (field) => (event) =>
    setForm((prev) => ({ ...prev, [field]: event.target.value }));

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setSubmitting(true);

    try {
      // Registering does not return tokens, so the two calls are separate.
      await registerRequest(form);
    } catch (err) {
      setError(
        err?.response?.status === 409
          ? "That username or email is already registered."
          : describeApiError(err, "Could not create the account."),
      );
      setSubmitting(false);
      return;
    }

    try {
      await login({ identifier: form.username, password: form.password });
      navigate("/", { replace: true });
    } catch {
      // Separating the two messages matters: the account really was created,
      // and telling them "registration failed" would be wrong.
      setNotice(
        "Your account was created, but signing you in automatically failed. Please sign in from the login page.",
      );
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm space-y-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold text-white">Create an account</h1>
          <p className="text-sm text-slate-400">It takes a moment.</p>
        </header>

        {error ? <Alert>{error}</Alert> : null}
        {notice ? <Alert tone="warning">{notice}</Alert> : null}

        <form onSubmit={handleSubmit} className="space-y-4">
          <Field
            label="Username"
            htmlFor="username"
            hint="3–30 characters; letters, numbers and underscores only."
          >
            <Input
              id="username"
              name="username"
              autoComplete="username"
              required
              minLength={3}
              maxLength={30}
              pattern="[A-Za-z0-9_]+"
              value={form.username}
              onChange={update("username")}
            />
          </Field>

          <Field label="Email" htmlFor="email">
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={form.email}
              onChange={update("email")}
            />
          </Field>

          <Field label="Password" htmlFor="password" hint="At least 8 characters.">
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              maxLength={128}
              value={form.password}
              onChange={update("password")}
            />
          </Field>

          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? <Spinner /> : null}
            Create account
          </Button>
        </form>

        <p className="text-sm text-slate-400">
          Already registered?{" "}
          <Link to="/login" className="text-accent hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
