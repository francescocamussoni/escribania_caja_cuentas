import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { apiPost, getAuthToken, postChangePasswordMe, setAuthToken } from "../services/api";

const TOKEN_KEY = "auth_token";
const ROL_KEY = "auth_rol";
const USERNAME_KEY = "auth_username";

export type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  rol: string;
};

type AuthState = {
  token: string | null;
  rol: string | null;
  username: string | null;
};

type AuthContextValue = AuthState & {
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<LoginResponse>;
  changePassword: (
    currentPassword: string,
    newPassword: string,
    newPasswordConfirm: string,
  ) => Promise<void>;
  logout: () => void;
};

function readStoredAuth(): AuthState {
  return {
    token: sessionStorage.getItem(TOKEN_KEY),
    rol: sessionStorage.getItem(ROL_KEY),
    username: sessionStorage.getItem(USERNAME_KEY),
  };
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [{ token, rol, username }, setAuthState] =
    useState<AuthState>(readStoredAuth);

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
    sessionStorage.setItem(USERNAME_KEY, username);
    setAuthToken(response.access_token);
    setAuthState({
      token: response.access_token,
      rol: response.rol,
      username,
    });
    return response;
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(ROL_KEY);
    sessionStorage.removeItem(USERNAME_KEY);
    setAuthToken(null);
    setAuthState({ token: null, rol: null, username: null });
  }, []);

  const changePassword = useCallback(
    async (
      currentPassword: string,
      newPassword: string,
      newPasswordConfirm: string,
    ) => {
      await postChangePasswordMe({
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      });
      logout();
    },
    [logout],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      rol,
      username,
      isAuthenticated: Boolean(token ?? getAuthToken()),
      login,
      changePassword,
      logout,
    }),
    [token, rol, username, login, changePassword, logout],
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
