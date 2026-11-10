import { type FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";

import { ApiError, api } from "../api";
import { PasswordField } from "../components/PasswordField";
import { setSession, useSession } from "../session";

export function AuthPage() {
  const session = useSession();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (session) return <Navigate to={session.role === "admin" ? "/admin/users" : "/"} replace />;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const login = String(form.get("login"));
    const password = String(form.get("password"));
    setBusy(true);
    setError(null);
    try {
      const res = await api.login(login, password);
      setSession({ token: res.access_token, login: res.user.login, role: res.user.role });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Нет связи с сервером");
    } finally {
      setBusy(false);
    }
  }

  return <section className="card auth">
    <h1>Вход</h1>
    <form onSubmit={onSubmit}>
      <label>Логин<input name="login" autoComplete="username" required autoFocus maxLength={64} /></label>
      <PasswordField label="Пароль" name="password" autoComplete="current-password" required />
      {error && <p role="alert" className="error">{error}</p>}
      <button className="btn" disabled={busy}>{busy ? "Входим…" : "Войти"}</button>
    </form>
    <p className="muted">Для получения аккаунта или сброса пароля обратитесь к администратору.</p>
  </section>;
}
