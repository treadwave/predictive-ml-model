import { Navigate, NavLink, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { Alerts } from "./pages/Alerts";
import { AuthPage } from "./pages/Auth";
import { EquipmentCard } from "./pages/EquipmentCard";
import { EquipmentList } from "./pages/EquipmentList";
import { setSession, useSession } from "./session";

export function App() {
  const session = useSession();

  return (
    <>
      <header className="header">
        <span className="logo">OFF-Tech</span>
        {session && (
          <>
            <nav>
              <NavLink to="/" end>
                Оборудование
              </NavLink>
              <NavLink to="/alerts">Алерты</NavLink>
            </nav>
            <div className="user">
              <span className="user-email">{session.email}</span>
              <button className="btn btn-secondary" onClick={() => setSession(null)}>
                Выйти
              </button>
            </div>
          </>
        )}
      </header>

      <main className="main">
        <Routes>
          <Route path="/login" element={<AuthPage key="login" mode="login" />} />
          <Route path="/register" element={<AuthPage key="register" mode="register" />} />
          <Route element={<RequireAuth />}>
            <Route path="/" element={<EquipmentList />} />
            <Route path="/equipment/:id" element={<EquipmentCard />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="*" element={<p>Страница не найдена</p>} />
          </Route>
        </Routes>
      </main>
    </>
  );
}

function RequireAuth() {
  const session = useSession();
  const location = useLocation();

  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  return <Outlet />;
}
