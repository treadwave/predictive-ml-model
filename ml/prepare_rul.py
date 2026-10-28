
import argparse
from pathlib import Path

import pandas as pd

OP_COLS = ["op1", "op2", "op3"]
SENSOR_COLS = [f"s{i}" for i in range(1, 22)]
COLUMNS = ["unit", "cycle"] + OP_COLS + SENSOR_COLS

SENSOR_INFO = {
    "s1": "T2 — температура на входе вентилятора", "s2": "T24 — температура на выходе КНД",
    "s3": "T30 — температура на выходе КВД", "s4": "T50 — температура на выходе ТНД",
    "s5": "P2 — давление на входе вентилятора", "s6": "P15 — давление в байпасном канале",
    "s7": "P30 — давление на выходе КВД", "s8": "Nf — физ. скорость вентилятора",
    "s9": "Nc — физ. скорость ядра", "s10": "epr — степень повышения давления",
    "s11": "Ps30 — статическое давление на выходе КВД", "s12": "phi — расход топлива / Ps30",
    "s13": "NRf — приведённая скорость вентилятора", "s14": "NRc — приведённая скорость ядра",
    "s15": "BPR — степень двухконтурности", "s16": "farB — топливо/воздух в камере сгорания",
    "s17": "htBleed — энтальпия отбора", "s18": "Nf_dmd — заданная скорость вентилятора",
    "s19": "PCNfR_dmd — заданная приведённая скорость", "s20": "W31 — охлаждающий отбор ТВД",
    "s21": "W32 — охлаждающий отбор ТНД",
}


def load_train(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=r"\s+", header=None)
    df = df.dropna(axis=1, how="all")  
    df.columns = COLUMNS
    return df


def add_rul(df: pd.DataFrame, clip: int | None = None) -> pd.DataFrame:
    """RUL = (последний цикл двигателя) - (текущий цикл). В последнем цикле RUL = 0 (отказ)."""
    df = df.copy()
    df["max_cycle"] = df.groupby("unit")["cycle"].transform("max")
    df["rul"] = df["max_cycle"] - df["cycle"]
    if clip:
        df["rul_clipped"] = df["rul"].clip(upper=clip)  # кусочно-линейный RUL
    return df.drop(columns="max_cycle")


def analyze_sensors(df: pd.DataFrame, std_eps: float = 1e-6) -> pd.DataFrame:
    rows = []
    for c in SENSOR_COLS:
        corr = df[c].corr(df["rul"], method="spearman")
        rows.append({"датчик": c, "описание": SENSOR_INFO[c], "std": df[c].std(),
                     "уникальных": df[c].nunique(), "spearman_с_RUL": corr,
                     "константа": df[c].std() < std_eps})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--clip", type=int, default=125)
    ap.add_argument("--out", type=Path, default=Path("data/processed"))
    a = ap.parse_args()

    df = add_rul(load_train(a.path), clip=a.clip)
    print(f"Строк: {len(df)}, двигателей: {df['unit'].nunique()}")
    life = df.groupby("unit")["cycle"].max()
    print(f"Жизнь двигателя (циклов): min={life.min()}, mean={life.mean():.0f}, max={life.max()}")
    print(f"Пропусков: {int(df.isna().sum().sum())}")
    print(f"Уникальных режимов работы (op1..3, округл.): "
          f"{df[OP_COLS].round(0).drop_duplicates().shape[0]}")

    rep = analyze_sensors(df)
    pd.set_option("display.width", 200, "display.max_colwidth", 50)
    print("\n", rep.round(3).to_string(index=False))
    print("\nКонстантные датчики (кандидаты на удаление):", rep.loc[rep["константа"], "датчик"].tolist())

    a.out.mkdir(parents=True, exist_ok=True)
    out = a.out / (a.path.stem + "_rul.csv")
    df.to_csv(out, index=False)
    rep.to_csv(a.out / (a.path.stem + "_sensor_report.csv"), index=False)
    print("Сохранено:", out)


if __name__ == "__main__":
    main()
