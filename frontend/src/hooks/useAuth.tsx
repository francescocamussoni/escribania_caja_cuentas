import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { apiPost, getAuthToken, setAuthToken } from "../services/api";

const TOKEN_KEY = "auth_token";
const ROL_KEY = "auth_rol";

export type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  rol: string;
};

type AuthState = {
  token: string | null;
  rol: string | null;
};

type AuthContextValue = AuthState & {
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<LoginResponse>;
  logout: () => void;
};

function readStoredAuth(): AuthState {
  return {
    token: sessionStorage.getItem(TOKEN_KEY),
    rol: sessionStorage.getItem(ROL_KEY),
  };
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [{ token, rol }, setAuthState] = useState<AuthState>(readStoredAuth);

  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  const login = useCallback(async (username: string, password: string) => {
    const response = await apiPost<LoginResponse>("/api/v1/auth/login", {
      username,
      password,
    });
    sessionStorage.setItem(TOKEN_KEY, response.access_token);
    sessionStorage.setItem(ROL_KEY, response.rol);
    setAuthToken(response.access_token);
    setAuthState({ token: response.access_token, rol: response.rol });
    return response;
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(ROL_KEY);
    setAuthToken(null);
    setAuthState({ token: null, rol: null });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      rol,
      isAuthenticated: Boolean(token ?? getAuthToken()),
      login,
      logout,
    }),
    [token, rol, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth debe usarse dentro de AuthProvider");
  }
  return context;
}
