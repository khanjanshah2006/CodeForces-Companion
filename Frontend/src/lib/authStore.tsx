/**
 * authStore.tsx — Auth Context for Codeforces TLE Ownership Verification
 *
 * Provides:
 *   - user: { cfHandle } | null
 *   - isAuthenticated: boolean
 *   - isRestoringSession: boolean (true on first mount while getMe() runs)
 *   - logout(): clears token + resets state
 *
 * On mount: calls getMe() to restore session from an existing localStorage JWT.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { getMe, clearAuthToken } from "./api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface AuthUser {
  cfHandle: string;
}

interface AuthStore {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isRestoringSession: boolean;
  logout: () => void;
  /** Call after a successful TLE verification to hydrate the context. */
  setAuthenticatedUser: (cfHandle: string) => void;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------
const AuthContext = createContext<AuthStore | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isRestoringSession, setIsRestoringSession] = useState(true);

  // On first mount: try to restore an existing JWT from localStorage.
  useEffect(() => {
    (async () => {
      try {
        const me = await getMe();
        setUser({ cfHandle: me.cf_handle });
      } catch {
        // Token missing, expired, or invalid — stay logged out.
        clearAuthToken();
      } finally {
        setIsRestoringSession(false);
      }
    })();
  }, []);

  const setAuthenticatedUser = useCallback((cfHandle: string) => {
    setUser({ cfHandle });
  }, []);

  const logout = useCallback(() => {
    clearAuthToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: user !== null,
        isRestoringSession,
        logout,
        setAuthenticatedUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export function useAuth(): AuthStore {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
