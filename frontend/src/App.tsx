import { useEffect, useState } from "react";
import { Navigate, NavLink, Outlet, Route, Routes } from "react-router-dom";

import { api } from "./api";
import { Alerts } from "./pages/Alerts";
import { AuthPage } from "./pages/Auth";
import { Users } from "./pages/Users";
import { EquipmentCard } from "./pages/EquipmentCard";
import { EquipmentList } from "./pages/EquipmentList";
import { getToken, setSession, useSession } from "./session";

export function App() {
  const session = useSession();
  const token = session?.token;
  const [verifiedToken, setVerifiedToken] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError("");
    if (!token) { setVerifiedToken(null); return; }
    // Check the stored session with the server before rendering protected pages.
    api.me().then(user => {
      if (cancelled || getToken() !== token) return;
      setSession({ token, login: user.login, role: user.role });
      setVerifiedToken(token);
    }).catch(() => {
      if (!cancelled && getToken() === token) setError("Не удалось проверить сессию. Проверьте соединение с сервером.");
    });
    return () => { cancelled = true; };
  }, [token, retry]);

  if (token && verifiedToken !== token) return <main className="main">
    {error ? <div role="alert" className="error">{error} <button className="btn" onClick={() => setRetry(n => n + 1)}>Повторить</button>
      <button className="btn btn-secondary" onClick={() => setSession(null)}>К странице входа</button></div>
      : <p role="status">Проверяем сессию…</p>}
  </main>;

  return <>
    <header className="header">
      <span className="logo">OFF-Tech</span>
      {session && <>
        <nav aria-label="Основные разделы">
          <NavLink to="/" end>Оборудование</NavLink>
          <NavLink to="/alerts">Алерты</NavLink>
          {session.role === "admin" && <NavLink to="/admin/users">Пользователи</NavLink>}
        </nav>
        <div className="user"><span className="user-login">{session.login}</span>
          <button className="btn btn-secondary" onClick={() => setSession(null)}>Выйти</button>
        </div>
      </>}
    </header>
    <main className="main">
      <Routes>
        <Route path="/login" element={<AuthPage />} />
        <Route element={<RequireAuth />}>
          <Route path="/" element={<EquipmentList />} />
          <Route path="/equipment/:id" element={<EquipmentCard />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/admin/users" element={session?.role === "admin" ? <Users /> : <Navigate to="/" replace />} />
        </Route>
        <Route path="*" element={<p>Страница не найдена</p>} />
      </Routes>
    </main>
  </>;
}

function RequireAuth() {
  return useSession() ? <Outlet /> : <Navigate to="/login" replace />;
}
