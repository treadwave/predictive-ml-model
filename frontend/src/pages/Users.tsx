import { type FormEvent, useEffect, useState } from "react";
import { api, ApiError, type ManagedUser } from "../api";

import { PasswordField } from "../components/PasswordField";

const PAGE_SIZE = 50;
const PASSWORD_HINT = "От 12 символов.";
function message(error: unknown) {
  return error instanceof ApiError ? error.detail : "Нет связи с сервером";
}

export function Users() {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<ManagedUser | "new" | null>(null);
  const [statusTarget, setStatusTarget] = useState<ManagedUser | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    api.listUsers(offset).then(rows => { if (!cancelled) setUsers(rows); })
      .catch(err => { if (!cancelled) setError(message(err)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [offset, reload]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password"));
    if (password !== form.get("confirm")) { setError("Пароли не совпадают"); return; }
    if (new TextEncoder().encode(password).length > 72) {
      let bytes = 0;
      let limit = 0;
      for (const character of password) {
        bytes += new TextEncoder().encode(character).length;
        if (bytes > 72) break;
        limit++;
      }
      setError(`Пароль слишком длинный. Сократите его до ${limit} символов.`);
      return;
    }
    if (!editing) return;
    setBusy(true); setError(""); setNotice("");
    try {
      if (editing === "new") {
        const user = await api.createUser(String(form.get("login")), password);
        setNotice(`Пользователь ${user.login} создан.`);
      } else {
        await api.resetPassword(editing.id, password);
        setNotice(`Пароль пользователя ${editing.login} изменён.`);
      }
      setEditing(null); // Unmount the form and discard password values.
      setReload(n => n + 1);
    } catch (err) { setError(message(err)); }
    finally { setBusy(false); }
  }

  async function changeStatus() {
    if (!statusTarget) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const user = await api.setUserActive(statusTarget.id, !statusTarget.is_active);
      setNotice(user.is_active ? `Пользователь ${user.login} разблокирован.`
        : `Пользователь ${user.login} заблокирован.`);
      setStatusTarget(null); setReload(n => n + 1);
    } catch (err) { setError(message(err)); }
    finally { setBusy(false); }
  }

  return <>
    <div className="page-head"><h1>Пользователи</h1>
      <button className="btn" disabled={busy || editing !== null || statusTarget !== null}
        onClick={() => { setEditing("new"); setError(""); setNotice(""); }}>Создать пользователя</button>
    </div>
    {error && <p role="alert" className="error">{error}</p>}
    {notice && <p role="status" className="success">{notice}</p>}
    {editing && <section className="card account-form" aria-labelledby="account-form-title">
      <h2 id="account-form-title">{editing === "new" ? "Новый пользователь" : `Новый пароль: ${editing.login}`}</h2>
      <form onSubmit={save} key={editing === "new" ? "new" : editing.id}>
        {editing === "new" && <label>Логин
          <input name="login" required minLength={3} maxLength={64} autoComplete="off" autoFocus
            aria-describedby="login-hint" />
          <span className="muted" id="login-hint">От 3 до 64 символов.</span>
        </label>}
        <PasswordField label="Пароль" name="password" required minLength={12} autoComplete="new-password"
          aria-describedby="password-hint" autoFocus={editing !== "new"} />
        <p className="muted" id="password-hint">{PASSWORD_HINT}</p>
        <PasswordField label="Повторите пароль" name="confirm" required minLength={12} autoComplete="new-password" />
        {editing !== "new" && <p>После смены пароля пользователю потребуется войти заново.</p>}
        <div className="actions"><button className="btn" disabled={busy}>{busy ? "Сохраняем…" : "Сохранить"}</button>
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => { setEditing(null); setError(""); }}>Отмена</button></div>
      </form>
    </section>}
    {statusTarget && <section className="card account-form" aria-labelledby="status-title">
      <h2 id="status-title">{statusTarget.is_active ? "Заблокировать" : "Разблокировать"} {statusTarget.login}?</h2>
      <p>{statusTarget.is_active ? "Пользователь потеряет доступ к системе."
        : "Пользователь снова сможет войти с текущим паролем."}</p>
      <div className="actions"><button className="btn" disabled={busy} onClick={changeStatus}>Подтвердить</button>
        <button className="btn btn-secondary" disabled={busy} onClick={() => setStatusTarget(null)}>Отмена</button></div>
    </section>}
    {loading ? <p role="status">Загружаем пользователей…</p> : <>
      <div className="table-scroll"><table className="table">
        <thead><tr><th>Логин</th><th>Роль</th><th>Состояние</th><th>Действия</th></tr></thead>
        <tbody>{users.map(user => <tr key={user.id}>
          <td>{user.login}</td><td>{user.role === "admin" ? "Администратор" : "Пользователь"}</td>
          <td><span className={`badge badge-${user.is_active ? "normal" : "critical"}`}>{user.is_active ? "Активен" : "Заблокирован"}</span></td>
          <td>{user.role === "employee" ? <div className="actions">
            <button className="btn btn-secondary" disabled={busy || editing !== null || statusTarget !== null}
              onClick={() => { setEditing(user); setError(""); setNotice(""); }}>Сбросить пароль</button>
            <button className="btn btn-secondary" disabled={busy || editing !== null || statusTarget !== null}
              onClick={() => { setStatusTarget(user); setError(""); setNotice(""); }}>{user.is_active ? "Заблокировать" : "Разблокировать"}</button>
          </div> : <span className="muted">Управление через сервер</span>}</td>
        </tr>)}</tbody>
      </table></div>
      {users.length === 0 && <p>На этой странице нет аккаунтов.</p>}
    </>}
    <div className="actions pagination">
      <button className="btn btn-secondary" disabled={loading || busy || offset === 0} onClick={() => setOffset(n => Math.max(0, n - PAGE_SIZE))}>Назад</button>
      <span>Страница {offset / PAGE_SIZE + 1}</span>
      <button className="btn btn-secondary" disabled={loading || busy || users.length < PAGE_SIZE} onClick={() => setOffset(n => n + PAGE_SIZE)}>Далее</button>
      <button className="btn btn-secondary" disabled={loading || busy} onClick={() => setReload(n => n + 1)}>Обновить</button>
    </div>
  </>;
}
