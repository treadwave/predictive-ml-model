import argparse
import os
from pathlib import Path

import pandas as pd
import xgboost as xgb
from dotenv import load_dotenv
from prepare_rul import add_rul, load_train
from sklearn.metrics import root_mean_squared_error

load_dotenv()

MODEL_PATH=os.getenv("MODEL_PATH")

def get_prepared_data(path: Path, max_clip: int) -> pd.DataFrame:
    df = load_train(path)
    df_with_rul = add_rul(df, max_clip)
    df_with_rul = df_with_rul.drop(columns=['s1', 's5', 's6', 's10', 's16', 's18', 's19', 'op1', 'op2', 'op3', 'rul'])

    return df_with_rul

def get_learning_data(df: pd.DataFrame) -> pd.DataFrame:
    df_learning = df[df['unit'] <= 66]

    return df_learning

def get_validation_data(df: pd.DataFrame) -> pd.DataFrame:
    df_validation = df[(df['unit'] > 66) & (df['unit'] <= 80)]

    return df_validation

def learning(df: pd.DataFrame):
    df_learning = get_learning_data(df)
    df_learning_x = df_learning.drop(columns=['rul_clipped', 'unit', 'cycle'])
    df_validation = get_validation_data(df)
    df_validation_x = df_validation.drop(columns=['rul_clipped', 'unit', 'cycle'])

    X_train, y_train = df_learning_x, df_learning['rul_clipped']
    X_validation, y_validation = df_validation_x, df_validation['rul_clipped']

    model = xgb.XGBRegressor(n_estimators=1000, learning_rate=0.05, early_stopping_rounds=50)
    model.fit(X_train, y_train, eval_set= [(X_validation, y_validation)])
    model.save_model(MODEL_PATH)

    y_pred = model.predict(X_validation)
    print(root_mean_squared_error(y_validation, y_pred))

    return model

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--clip", type=int, default=125)
    a = ap.parse_args()

    df_main = get_prepared_data(a.path, a.clip)

    learning(df_main)

if __name__ == "__main__":
    main()


