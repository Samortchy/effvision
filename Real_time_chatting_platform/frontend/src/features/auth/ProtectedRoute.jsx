import { Navigate, useLocation } from "react-router-dom";

import { Spinner } from "../../components/ui";
import { useAuthStore } from "../../stores/authStore";

/**
 * Gate for authenticated routes.
 *
 * The "unknown" status matters: on a hard reload the access token is gone
 * (memory-only) and bootstrap is still exchanging the refresh token. Rendering
 * the login page during that window would bounce an authenticated user out for
 * no reason, so it waits instead.
 */
export default function ProtectedRoute({ children }) {
  const status = useAuthStore((state) => state.status);
  const location = useLocation();

  if (status === "unknown") {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  if (status !== "authenticated") {
    // Remember where they were headed so login can send them back.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return children;
}
