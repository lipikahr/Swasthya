import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { api, clearTokens, saveTokens } from "./api";

export type User = { id: number; email: string; name: string };

type SessionValue = {
  user: User | null;
  ready: boolean;
  register: (email: string, name: string, password: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api<User>("/api/auth/me/")
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setReady(true));
  }, []);

  async function register(email: string, name: string, password: string) {
    const body = await api<{ user: User; access: string; refresh: string }>("/api/auth/register/", {
      method: "POST",
      body: JSON.stringify({ email, name, password }),
    });
    saveTokens(body.access, body.refresh);
    setUser(body.user);
  }

  async function login(email: string, password: string) {
    const tokens = await api<{ access: string; refresh: string }>("/api/auth/login/", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    saveTokens(tokens.access, tokens.refresh);
    setUser(await api<User>("/api/auth/me/"));
  }

  async function logout() {
    const refresh = sessionStorage.getItem("swasthya.refresh");
    navigate("/", { replace: true });
    try {
      if (refresh) {
        await api("/api/auth/logout/", { method: "POST", body: JSON.stringify({ refresh }) });
      }
    } finally {
      clearTokens();
      setUser(null);
    }
  }

  return (
    <SessionContext.Provider value={{ user, ready, register, login, logout }}>{children}</SessionContext.Provider>
  );
}

export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("Session is missing.");
  return value;
}
