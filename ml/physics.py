"""Физическая модель деградации турбовентиляторного двигателя.

Фактическая деградация по датчикам: проекция нормированных показаний 14 рабочих датчиков на главное
направление их изменения (первая главная компонента), отмасштабированная так, что 0 соответствует
исправному двигателю (первые 20 циклов), а 1 — отказу (последние 5 циклов) на обучающих двигателях.

Ожидаемая деградация: экспоненциальный закон накопления повреждений D(τ) = a·(e^(b·τ) − 1), которым
NASA моделировала износ при генерации C-MAPSS (Saxena et al., 2008). τ — эквивалентная наработка:
каждый цикл добавляет к ней коэффициент ускорения по Аррениусу от температуры воздуха из Open-Meteo,
AF = exp(Ea/R · (1/T_ref − 1/T)). T_ref = 288,15 K (15 °C) — стандартная атмосфера, в которой сняты
данные C-MAPSS, поэтому при 15 °C AF = 1.

Невязка (residual) — фактическая деградация минус ожидаемая: больше нуля, если двигатель изнашивается
быстрее, чем предсказывает физическая модель.
"""

import json
import logging
import math
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from prepare_rul import load_train
from scipy.optimize import curve_fit

logger = logging.getLogger("physics")

SENSORS = ["s2", "s3", "s4", "s7", "s8", "s9", "s11", "s12", "s13", "s14", "s15", "s17", "s20", "s21"]
TRAIN_UNITS = 80  # двигатели 81–100 проигрывает симулятор, в обучение они не попадают
HEALTHY_CYCLES = 20
FAILED_CYCLES = 5

GAS_CONSTANT = 8.314  # Дж/(моль·К)
T_REF = 288.15  # К
ACTIVATION_ENERGY = 8000.0  # Дж/моль: AF ≈ 0,63 при −20 °C и ≈ 1,24 при +35 °C
SMOOTHING = 0.3  # коэффициент экспоненциального сглаживания фактической деградации

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_TTL_SEC = 3600
WEATHER_RETRY_SEC = 300


def damage(tau, a, b):
    return a * (np.exp(b * tau) - 1.0)


@dataclass(frozen=True)
class PhysicsModel:
    mean: np.ndarray
    std: np.ndarray
    direction: np.ndarray
    healthy: float
    failed: float
    a: float
    b: float

    def observed(self, sensors: np.ndarray) -> np.ndarray:
        """Фактическая деградация по показаниям: строки — циклы, колонки — SENSORS."""
        score = ((sensors - self.mean) / self.std) @ self.direction
        return (score - self.healthy) / (self.failed - self.healthy)

    def expected(self, tau: float) -> float:
        return float(damage(tau, self.a, self.b))

    def age(self, degradation: float) -> float:
        """Эквивалентная наработка по ожидаемой деградации — функция, обратная expected."""
        return math.log(degradation / self.a + 1.0) / self.b


def fit(path: Path) -> PhysicsModel:
    df = load_train(path)
    df = df[df["unit"] <= TRAIN_UNITS]

    x = df[SENSORS].to_numpy(dtype=float)
    mean, std = x.mean(axis=0), x.std(axis=0)
    z = (x - mean) / std
    _, _, vt = np.linalg.svd(z, full_matrices=False)
    direction = vt[0]

    score = z @ direction
    cycle = df["cycle"].to_numpy(dtype=float)
    life = df.groupby("unit")["cycle"].transform("max").to_numpy()
    healthy = score[cycle <= HEALTHY_CYCLES].mean()
    failed = score[cycle > life - FAILED_CYCLES].mean()
    observed = (score - healthy) / (failed - healthy)

    (a, b), _ = curve_fit(damage, cycle, observed, p0=(0.5, 0.004), maxfev=20000)
    logger.info("physics model: D(t) = %.4f * (exp(%.5f * t) - 1)", a, b)
    return PhysicsModel(mean, std, direction, float(healthy), float(failed), float(a), float(b))


def acceleration(temperature: float | None, activation_energy: float = ACTIVATION_ENERGY) -> float:
    """Коэффициент ускорения износа по Аррениусу; без погоды — 1."""
    if temperature is None:
        return 1.0
    kelvin = temperature + 273.15
    return math.exp(activation_energy / GAS_CONSTANT * (1.0 / T_REF - 1.0 / kelvin))


def predict(model: PhysicsModel, readings: pd.DataFrame, state: dict[int, tuple[int, float, float]],
            factor: float, smoothing: float = SMOOTHING) -> pd.DataFrame:
    """Ожидаемая деградация и невязка для новых показаний.

    readings — новые строки sensor_readings, отсортированные по (equipment_id, cycle).
    state — последнее посчитанное состояние по оборудованию: цикл, ожидаемая деградация и сглаженная
    фактическая. Функция дополняет его, чтобы следующая пачка продолжила накопление.
    """
    observed = model.observed(readings[SENSORS].to_numpy(dtype=float))
    rows = []
    for equipment_id, cycle, raw in zip(readings["equipment_id"], readings["cycle"], observed):
        equipment_id, cycle, raw = int(equipment_id), int(cycle), float(raw)
        previous = state.get(equipment_id)
        if previous is None:
            tau, actual = cycle * factor, raw
        else:
            last_cycle, last_expected, last_actual = previous
            tau = model.age(last_expected) + (cycle - last_cycle) * factor
            actual = smoothing * raw + (1.0 - smoothing) * last_actual
        expected = model.expected(tau)
        state[equipment_id] = (cycle, expected, actual)
        rows.append((equipment_id, cycle, expected, actual - expected))
    return pd.DataFrame(rows, columns=["equipment_id", "cycle", "predicted_degradation", "residual"])


class Weather:
    """Температура воздуха из Open-Meteo с кэшем на час.

    Если API недоступен, используется последнее полученное значение; если значения ещё нет,
    модель работает без погодного фактора.
    """

    def __init__(self, latitude: float, longitude: float, fetch: Callable[[], float] | None = None,
                 ttl: float = WEATHER_TTL_SEC, retry: float = WEATHER_RETRY_SEC):
        self.latitude = latitude
        self.longitude = longitude
        self.ttl = ttl
        self.retry = retry
        self._fetch = fetch or self._fetch_open_meteo
        self._value: float | None = None
        self._next_fetch = 0.0

    def _fetch_open_meteo(self) -> float:
        query = urllib.parse.urlencode({"latitude": self.latitude, "longitude": self.longitude,
                                        "current": "temperature_2m"})
        with urllib.request.urlopen(f"{OPEN_METEO_URL}?{query}", timeout=5) as response:
            return float(json.load(response)["current"]["temperature_2m"])

    def temperature(self) -> float | None:
        now = time.monotonic()
        if now < self._next_fetch:
            return self._value
        try:
            self._value = self._fetch()
            self._next_fetch = now + self.ttl
            logger.info("open-meteo: %.1f °C, acceleration %.3f", self._value, acceleration(self._value))
        except (OSError, ValueError, KeyError, TypeError) as error:
            self._next_fetch = now + self.retry
            fallback = "last cached value" if self._value is not None else "no weather factor"
            logger.warning("open-meteo unavailable (%s), using %s", error, fallback)
        return self._value
