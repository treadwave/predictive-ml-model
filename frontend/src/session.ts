import { useSyncExternalStore } from "react";

export interface Session {
  token: string;
  login: string;
  role: "admin" | "employee";
}

const KEY = "offtech.session";
const listeners = new Set<() => void>();

function read(): Session | null {
  try {
    const value = JSON.parse(localStorage.getItem(KEY) ?? "null");
    return typeof value?.token === "string" && typeof value?.login === "string" && (value.role === "admin" || value.role === "employee") ? value : null;
  } catch {
    return null;
  }
}

let session = read();

function notify(): void {
  listeners.forEach((l) => l());
}

export function getToken(): string | null {
  return session?.token ?? null;
}

export function setSession(next: Session | null): void {
  session = next;
  try {
    if (next) localStorage.setItem(KEY, JSON.stringify(next));
    else localStorage.removeItem(KEY);
  } catch {
  }
  notify();
}

// Вход и выход в соседней вкладке.
window.addEventListener("storage", (e) => {
  if (e.key !== KEY && e.key !== null) return;
  session = read();
  notify();
});

export function useSession(): Session | null {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => session,
    () => null,
  );
}
