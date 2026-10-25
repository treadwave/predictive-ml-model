from sqlalchemy import create_engine, text
import xgboost as xgb
import pandas as pd
import os
from dotenv import load_dotenv
import numpy as np
import time
import logging
import sys

logger = logging.getLogger("worker")

load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"))

def get_model() -> xgb.XGBRegressor:
    model = xgb.XGBRegressor()
    model.load_model(os.getenv("MODEL_PATH"))

    return model

def get_data_from_simulator() -> tuple[pd.DataFrame, pd.DataFrame] | tuple[None, None]:
    with engine.connect() as connection:
        query = text("""
                    SELECT sensor_readings.*
                    FROM sensor_readings
                    LEFT JOIN ml_predictions
                    ON sensor_readings.equipment_id = ml_predictions.equipment_id
                    AND sensor_readings.cycle = ml_predictions.cycle
                    WHERE ml_predictions.id IS NULL
                    """)
        result = connection.execute(query)

        if (result.rowcount == 0):
            return None, None

        df = pd.DataFrame(result)
        df_for_pred = df.drop(columns=['id', 'equipment_id', 'cycle', 'rul', 'created_at'])
        df_for_pred['s17'] = df_for_pred['s17'].astype(int)

    return df_for_pred, df

def model_predict(df: pd.DataFrame, model: xgb.XGBRegressor) -> np.ndarray:
    arr = model.predict(df)

    return arr

def write_to_db():
    model = get_model()

    query_second = text("""
                    INSERT INTO ml_predictions (equipment_id, cycle, predicted_rul, defect_probability, residual, model_version)
                    VALUES (:eq_id, :cycle, :rul, 0, 0, :model)
                    ON CONFLICT DO NOTHING
                    """)

    try:
        while True:
            df_pred, df = get_data_from_simulator()

            if df_pred is None or df is None:
                logger.info("all processed")
                time.sleep(int(os.getenv("WORKER_POLL_INTERVAL")))
            else:
                t0 = time.perf_counter()
                arr = model_predict(df_pred, model)
                with engine.connect() as connection:

                    for i in range (arr.size):
                        df_row = df.iloc[i]
                        connection.execute(query_second, {'eq_id': df_row['equipment_id'], 'cycle': df_row['cycle'], 'rul':arr[i], 'model': 'first_xgboost_model'})

                    connection.commit()

                elapsed_ms = (time.perf_counter() - t0) * 1000
                logger.info("inserted %d rows in %.2f ms", arr.size, elapsed_ms)

    except KeyboardInterrupt:
        logger.warning("interrupted by user")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    write_to_db()


