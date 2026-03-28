import { createContext, useContext } from "react";
import { getStoredUser, clearTokens } from "@/lib/auth";

export interface AuthUser {
  username: string;
  role: string;
}

export interface AuthContextValue {
  user: AuthUser | null;
  logout: () => void;
  setUser: (u: AuthUser | null) => void;
}

export const AuthContext = createContext<AuthContextValue>({
  user: getStoredUser(),
  logout: () => {},
  setUser: () => {},
});

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}

export function createLogout(setUser: (u: AuthUser | null) => void) {
  return () => {
    clearTokens();
    setUser(null);
  };
}
