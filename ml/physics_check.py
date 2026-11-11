"""Проверка физмодели: обучение на двигателях 1–80, проверка на 81–100, которые проигрывает симулятор."""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import physics
from prepare_rul import load_train

logger = logging.getLogger("physics_check")


def check_model(path: Path) -> None:
    model = physics.fit(path)
    assert model.a > 0 and model.b > 0, "ожидаемая деградация должна расти с наработкой"

    df = load_train(path)
    df = df[df["unit"] > physics.TRAIN_UNITS].sort_values(["unit", "cycle"]).rename(columns={"unit": "equipment_id"})
    result = physics.predict(model, df, {}, factor=1.0)
    result["actual"] = result["predicted_degradation"] + result["residual"]

    life = result.groupby("equipment_id")["cycle"].transform("max")
    spearman = result["actual"].corr(result["cycle"] / life, method="spearman")
    logger.info("spearman(actual degradation, life fraction): %.3f", spearman)
    assert spearman > 0.6, "фактическая деградация должна расти к отказу"

    at_failure = result[result["cycle"] == life]
    corr = float(np.corrcoef(at_failure["cycle"], at_failure["residual"])[0, 1])
    logger.info("corr(life, residual at failure): %.3f", corr)
    assert corr < -0.5, "у быстро изнашивающихся двигателей невязка к отказу должна быть больше"

    for _, row in at_failure.iterrows():
        logger.info("unit %d: life %d, actual %.3f, expected %.3f, residual %+.3f", row["equipment_id"],
                    row["cycle"], row["actual"], row["predicted_degradation"], row["residual"])


def check_weather() -> None:
    assert physics.acceleration(None) == 1.0
    assert abs(physics.acceleration(15.0) - 1.0) < 1e-9
    assert physics.acceleration(0.0) < 1.0 < physics.acceleration(30.0)

    responses = []

    def flaky() -> float:
        if responses:
            return responses.pop()
        raise OSError("network is unreachable")

    assert physics.Weather(0, 0, fetch=flaky).temperature() is None, "без кэша — без погодного фактора"

    responses.append(20.0)
    weather = physics.Weather(0, 0, fetch=flaky, ttl=0, retry=0)
    assert weather.temperature() == 20.0
    assert weather.temperature() == 20.0, "при недоступности API используется последнее значение"
    logger.info("weather fallback: ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    a = ap.parse_args()

    pd.set_option("display.width", 200)
    check_model(a.path)
    check_weather()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    main()
