import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  changePasswordRequest,
  fetchMe,
  loginRequest,
  registerRequest,
  updateMeRequest,
  type ChangePasswordPayload,
  type LoginPayload,
  type RegisterPayload,
  type UpdateMePayload,
  type User,
} from "../lib/api";

const STORAGE_KEY = "patrimoineop_access_token";

type AuthContextValue = {
  token: string | null;
  user: User | null;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => void;
  refreshMe: () => Promise<void>;
  updateProfile: (payload: UpdateMePayload) => Promise<void>;
  changePassword: (payload: ChangePasswordPayload) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(Boolean(localStorage.getItem(STORAGE_KEY)));

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const refreshMe = useCallback(async () => {
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const currentUser = await fetchMe(token);
      setUser(currentUser);
    } catch {
      logout();
    } finally {
      setIsLoading(false);
    }
  }, [logout, token]);

  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  const login = useCallback(async (payload: LoginPayload) => {
    const response = await loginRequest(payload);
    localStorage.setItem(STORAGE_KEY, response.access_token);
    setToken(response.access_token);
    setUser(response.user);
    setIsLoading(false);
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    return registerRequest(payload);
  }, []);

  const updateProfile = useCallback(
    async (payload: UpdateMePayload) => {
      if (!token) {
        throw new Error("Authentification requise.");
      }

      const updatedUser = await updateMeRequest(token, payload);
      setUser(updatedUser);
    },
    [token],
  );

  const changePassword = useCallback(
    async (payload: ChangePasswordPayload) => {
      if (!token) {
        throw new Error("Authentification requise.");
      }

      await changePasswordRequest(token, payload);
    },
    [token],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isLoading,
      login,
      register,
      logout,
      refreshMe,
      updateProfile,
      changePassword,
    }),
    [changePassword, isLoading, login, logout, refreshMe, register, token, updateProfile, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return context;
}
