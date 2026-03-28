import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@/hooks/useAuth";
import type { AuthUser } from "@/hooks/useAuth";
import { getStoredUser, clearTokens } from "@/lib/auth";
import { ToastProvider } from "@/components/ui/Toast";
import { Layout } from "@/components/layout/Layout";
import { Login } from "@/pages/Login";
import { Dashboard } from "@/pages/Dashboard";
import { Bugs } from "@/pages/Bugs";
import { TestCases } from "@/pages/TestCases";
import { Projects } from "@/pages/Projects";
import { Requirements } from "@/pages/Requirements";
import { Employees } from "@/pages/Employees";
import { Query } from "@/pages/Query";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  const [user, setUser] = useState<AuthUser | null>(getStoredUser());

  const logout = () => {
    clearTokens();
    setUser(null);
    queryClient.clear();
  };

  return (
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={{ user, setUser, logout }}>
        <ToastProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route element={<Layout />}>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/query" element={<Query />} />
                <Route path="/bugs" element={<Bugs />} />
                <Route path="/test-cases" element={<TestCases />} />
                <Route path="/projects" element={<Projects />} />
                <Route path="/requirements" element={<Requirements />} />
                <Route path="/employees" element={<Employees />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </AuthContext.Provider>
    </QueryClientProvider>
  );
}
