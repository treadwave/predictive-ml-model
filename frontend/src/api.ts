import { getToken, setSession } from "./session";

export type Status = "normal" | "warning" | "critical";

export interface Equipment {
  id: number;
  name: string;
  type: string;
  unit_number: number;
  last_maintenance_date: string | null;
  current_cycle: number;
  status: Status;
  predicted_rul: number;
}

export interface EquipmentStatus {
  equipment_id: number;
  status: Status;
  current_cycle: number;
  predicted_rul: number;
  defect_probability: number;
  residual: number;
}

export interface Reading {
  cycle: number;
  sensors: Record<string, number>;
}

export interface PhysicsPoint {
  cycle: number;
  expected: number;
  actual: number;
  residual: number;
}

export interface ForecastPoint {
  cycle: number;
  rul: number;
  rul_low: number;
  rul_high: number;
}

export interface Forecast {
  equipment_id: number;
  current_cycle: number;
  predicted_rul: number;
  predicted_failure_cycle: number;
  points: ForecastPoint[];
}

export interface Alert {
  id: number;
  equipment_id: number;
  cycle: number;
  triggered_at: string;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface User {
  id: number;
  login: string;
  role: "admin" | "employee";
  is_active: boolean;
}

export interface ManagedUser extends User {
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers = new Headers(init?.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(BASE + path, { ...init, headers });
  if (!res.ok) {
    // Токен просрочен или пользователь удалён: выходим, RequireAuth откроет страницу входа.
    if (res.status === 401 && token && token === getToken()) setSession(null);
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: { msg: string }) => d.msg.replace(/^Value error, /, "")).join("; ");
    } catch {}
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function postJson(body: unknown): RequestInit {
  return { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

export const api = {
  listEquipment: () => request<Equipment[]>("/equipment"),
  getEquipment: (id: number) => request<Equipment>(`/equipment/${id}`),
  getHistory: (id: number, limit = 500) => request<Reading[]>(`/equipment/${id}/history?limit=${limit}`),
  getForecast: (id: number) => request<Forecast>(`/equipment/${id}/forecast`),
  getPhysics: (id: number, limit = 500) => request<PhysicsPoint[]>(`/equipment/${id}/physics?limit=${limit}`),
  listAlerts: (limit = 100) => request<Alert[]>(`/alerts?limit=${limit}`),
  alertsByEquipment: (id: number, limit = 50) => request<Alert[]>(`/alerts/${id}?limit=${limit}`),
  predict: (id: number) => request<EquipmentStatus>("/predict", postJson({ equipment_id: id })),
  login: (login: string, password: string) => request<AuthResponse>("/auth/login", postJson({ login, password })),
  me: () => request<User>("/auth/me"),
  listUsers: (offset = 0) => request<ManagedUser[]>(`/admin/users?limit=50&offset=${offset}`),
  createUser: (login: string, password: string) =>
    request<ManagedUser>("/admin/users", postJson({ login, password })),
  resetPassword: (id: number, password: string) =>
    request<void>(`/admin/users/${id}/password`, { ...postJson({ password }), method: "PUT" }),
  setUserActive: (id: number, is_active: boolean) =>
    request<ManagedUser>(`/admin/users/${id}/status`, { ...postJson({ is_active }), method: "PUT" }),
};
