import { type FormEvent, useState } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";

import { ApiError, api } from "../api";
import { setSession, useSession } from "../session";

const PASSWORD_MIN = 8;
const PASSWORD_MAX_BYTES = 72;

const MODES = {
  login: {
    title: "Вход",
    submit: "Войти",
    send: api.login,
    other: { question: "Нет аккаунта?", link: "Зарегистрироваться", to: "/register" },
  },
  register: {
    title: "Регистрация",
    submit: "Зарегистрироваться",
    send: api.register,
    other: { question: "Уже есть аккаунт?", link: "Войти", to: "/login" },
  },
};

export function AuthPage({ mode }: { mode: keyof typeof MODES }) {
  const session = useSession();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const page = MODES[mode];
  const register = mode === "register";

  if (session) {
    const from = (location.state as { from?: string } | null)?.from ?? "/";
    return <Navigate to={from} replace />;
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const email = String(form.get("email"));
    const password = String(form.get("password"));
    if (register && password !== form.get("confirm")) return setError("Пароли не совпадают");
    if (register && new TextEncoder().encode(password).length > PASSWORD_MAX_BYTES) {
      return setError(`Пароль слишком длинный: не больше ${PASSWORD_MAX_BYTES} байт`);
    }

    setBusy(true);
    setError(null);
    try {
      const res = await page.send(email, password);
      setSession({ token: res.access_token, email: res.user.email });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Нет связи с сервером");
      setBusy(false);
    }
  }

  return (
    <section className="card auth">
      <h1>{page.title}</h1>
      <form onSubmit={onSubmit}>
        <label>
          Email
          <input name="email" type="email" autoComplete="email" required autoFocus />
        </label>
        <label>
          Пароль
          <input
            name="password"
            type="password"
            autoComplete={register ? "new-password" : "current-password"}
            minLength={register ? PASSWORD_MIN : undefined}
            placeholder={register ? `Не короче ${PASSWORD_MIN} символов` : undefined}
            required
          />
        </label>
        {register && (
          <label>
            Повторите пароль
            <input name="confirm" type="password" autoComplete="new-password" required />
          </label>
        )}
        {error && <p className="error">{error}</p>}
        <button className="btn" disabled={busy}>
          {page.submit}
        </button>
      </form>
      <p className="muted">
        {page.other.question}{" "}
        <Link to={page.other.to} state={location.state}>
          {page.other.link}
        </Link>
      </p>
    </section>
  );
}
