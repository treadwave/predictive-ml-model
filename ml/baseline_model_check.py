from prepare_rul import load_train
import xgboost as xgb
from dotenv import load_dotenv
import os
from pathlib import Path
import argparse
import pandas as pd
import numpy as np
from sklearn.metrics import root_mean_squared_error

load_dotenv()
MODEL_PATH = os.getenv("MODEL_PATH")

def clip_rul(s):
    if (int(s) >= 125):
        return 125
    else:
        return s

def read_rul(path: Path) -> pd.Series:
    df = pd.read_csv(path, sep='\t', header=None, names=['rul'])
    df = df['rul'].apply(clip_rul)

    return df

def check_model(path: Path, rul_df: pd.Series) -> np.ndarray:
    model = xgb.XGBRegressor()
    model.load_model(MODEL_PATH)

    df = load_train(path)
    df = df.sort_values('cycle').groupby('unit').agg('last')
    df = df.drop(columns=['cycle', 'op1', 'op2', 'op3', 's1', 's5', 's6', 's10', 's16', 's19', 's18'])

    pred = model.predict(df)

    print(root_mean_squared_error(rul_df, pred))

    return pred

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--rul", type=Path)
    a = ap.parse_args()

    rul_df = read_rul(a.rul)
    arr = check_model(a.path, rul_df)

    for i in range(100):
        print(f"{i + 1}: {arr[i]}")

if __name__ == "__main__":
    main()