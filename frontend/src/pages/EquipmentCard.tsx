import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api } from "../api";
import { AlertsTable } from "../components/AlertsTable";
import { Empty, ErrorMessage, Loading } from "../components/State";
import { StatusBadge } from "../components/StatusBadge";
import { SENSORS, formatDate, formatRul } from "../format";
import { useFetch } from "../useFetch";

const RUL_WARNING = 75;
const RUL_CRITICAL = 30;

export function EquipmentCard() {
  const id = Number(useParams().id);
  const equipment = useFetch(() => api.getEquipment(id), [id]);

  const [recalculating, setRecalculating] = useState(false);
  const [recalcError, setRecalcError] = useState<string | null>(null);
  const [forecastVersion, setForecastVersion] = useState(0);

  async function recalculate() {
    setRecalculating(true);
    setRecalcError(null);
    try {
      const s = await api.predict(id);
      equipment.setData((prev) =>
        prev ? { ...prev, status: s.status, predicted_rul: s.predicted_rul, current_cycle: s.current_cycle } : prev,
      );
      setForecastVersion((v) => v + 1);
    } catch (e) {
      setRecalcError((e as Error).message);
    } finally {
      setRecalculating(false);
    }
  }

  if (equipment.error) return <ErrorMessage message={equipment.error} />;
  if (!equipment.data) return <Loading />;
  const e = equipment.data;

  return (
    <section>
      <Link to="/" className="back">
        ← К списку оборудования
      </Link>

      <div className="card card-head">
        <div>
          <h1>{e.name}</h1>
          <p className="muted">
            {e.type} · unit {e.unit_number} · цикл {e.current_cycle} · обслуживание {formatDate(e.last_maintenance_date)}
          </p>
        </div>
        <div className="head-right">
          <StatusBadge status={e.status} large />
          <div className="rul">
            <span className="rul-value">{formatRul(e.predicted_rul)}</span>
            <span className="rul-unit">циклов RUL</span>
          </div>
          <button className="btn" onClick={recalculate} disabled={recalculating}>
            {recalculating ? "Пересчёт…" : "Пересчитать прогноз"}
          </button>
        </div>
      </div>
      {recalcError && <ErrorMessage message={recalcError} />}

      <div className="grid">
        <ForecastChart id={id} version={forecastVersion} />
        <HistoryChart id={id} />
        <PhysicsChart />
        <EquipmentAlerts id={id} />
      </div>
    </section>
  );
}

function HistoryChart({ id }: { id: number }) {
  const [sensor, setSensor] = useState(SENSORS[0].code);
  const { data, error } = useFetch(() => api.getHistory(id), [id]);

  const points = (data ?? []).map((r) => ({ cycle: r.cycle, value: r.sensors[sensor] }));

  return (
    <div className="card">
      <div className="card-title">
        <h2>История показаний</h2>
        <select value={sensor} onChange={(ev) => setSensor(ev.target.value)}>
          {SENSORS.map((s) => (
            <option key={s.code} value={s.code}>
              {s.code} · {s.name}
            </option>
          ))}
        </select>
      </div>
      {error && <ErrorMessage message={error} />}
      {!data && !error && <Loading />}
      {data && data.length === 0 && <Empty text="Показаний пока нет." />}
      {data && data.length > 0 && (
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={points}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="cycle" label={{ value: "цикл", position: "insideBottomRight", offset: -4 }} />
            <YAxis domain={["auto", "auto"]} width={70} />
            <Tooltip formatter={(v: number) => [v, sensor]} labelFormatter={(c) => `Цикл ${c}`} />
            <Line type="monotone" dataKey="value" stroke="#2563eb" dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function ForecastChart({ id, version }: { id: number; version: number }) {
  const { data, error } = useFetch(() => api.getForecast(id), [id, version]);

  const points = (data?.points ?? []).map((p) => ({ ...p, range: [p.rul_low, p.rul_high] }));

  return (
    <div className="card">
      <div className="card-title">
        <h2>Прогноз RUL</h2>
        {data && <span className="muted">ожидаемый отказ: цикл {data.predicted_failure_cycle}</span>}
      </div>
      {error && <ErrorMessage message={error} />}
      {!data && !error && <Loading />}
      {data && (
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={points}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="cycle" label={{ value: "цикл", position: "insideBottomRight", offset: -4 }} />
            <YAxis width={50} />
            <Tooltip labelFormatter={(c) => `Цикл ${c}`} />
            <ReferenceLine y={RUL_WARNING} stroke="#d97706" strokeDasharray="4 4" />
            <ReferenceLine y={RUL_CRITICAL} stroke="#dc2626" strokeDasharray="4 4" />
            <Area dataKey="range" name="интервал" stroke="none" fill="#93c5fd" fillOpacity={0.4} isAnimationActive={false} />
            <Line dataKey="rul" name="RUL" stroke="#2563eb" dot={false} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function PhysicsChart() {
  return (
    <div className="card">
      <div className="card-title">
        <h2>Физическая модель против фактических показаний</h2>
      </div>
      <div className="placeholder">
        Заглушка
      </div>
    </div>
  );
}

function EquipmentAlerts({ id }: { id: number }) {
  const { data, error } = useFetch(() => api.alertsByEquipment(id), [id]);

  return (
    <div className="card">
      <div className="card-title">
        <h2>Алерты</h2>
      </div>
      {error && <ErrorMessage message={error} />}
      {!data && !error && <Loading />}
      {data && data.length === 0 && <Empty text="Алертов по этому двигателю нет." />}
      {data && data.length > 0 && <AlertsTable alerts={data} />}
    </div>
  );
}
