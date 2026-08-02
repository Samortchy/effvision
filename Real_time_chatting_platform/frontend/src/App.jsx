import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./features/auth/ProtectedRoute";
import LoginPage from "./features/auth/LoginPage";
import RegisterPage from "./features/auth/RegisterPage";
import AppLayout from "./components/AppLayout";
import ChatPanel from "./features/chat/ChatPanel";
import { EmptyState } from "./components/ui";
import { useAuthStore } from "./stores/authStore";

export default function App() {
  const bootstrap = useAuthStore((state) => state.bootstrap);

  // One attempt to resume a session from the stored refresh token.
  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route
          index
          element={
            <EmptyState title="No conversation selected">
              Search for someone in the sidebar to start a private conversation.
            </EmptyState>
          }
        />
        <Route path="c/:conversationId" element={<ChatPanel />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
