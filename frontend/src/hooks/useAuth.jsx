import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { login as apiLogin, register as apiRegister, logout as apiLogout, isAuthenticated } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isAuthenticated()) {
      // Restore user from stored data
      const stored = localStorage.getItem("userData");
      if (stored) {
        try {
          setUser(JSON.parse(stored));
        } catch {
          localStorage.removeItem("userData");
        }
      }
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (username, password) => {
    const data = await apiLogin(username, password);
    if (data.user) {
      localStorage.setItem("userData", JSON.stringify(data.user));
      setUser(data.user);
    }
    return data;
  }, []);

  const register = useCallback(async (userData) => {
    const data = await apiRegister(userData);
    return data;
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem("userData");
    apiLogout();
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}