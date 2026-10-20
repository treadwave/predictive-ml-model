from prepare_rul import add_rul, load_train
from datetime import date
import time

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Table, MetaData, text
from sqlalchemy.dialects.postgresql import insert

import pandas as pd
from pathlib import Path
import argparse
import logging
import sys

logger = logging.getLogger("simulator")

load_dotenv()

INTERVAL_SEC = int(os.getenv("SIMULATOR_WAIT_TIME", "30"))

def get_data() -> pd.DataFrame:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--clip", type=int, default=125)
    ap.add_argument("--out", type=Path, default=Path("data/processed"))
    a = ap.parse_args()

    df = add_rul(load_train(a.path), clip=a.clip)
    a.out.mkdir(parents=True, exist_ok=True)
    out = a.out / (a.path.stem + "_simulator_rul.csv")

    df = df[df['unit'] > 80]

    df = df.drop(columns=['s1', 's5', 's6', 's10', 's16', 's18', 's19'])

    df.to_csv(out, index=False)
    return df

def fill_db():
    engine = create_engine(os.getenv("DATABASE_URL"))

    df_sensors = get_data()
    df_equipment = df_sensors.drop(columns=['s3', 's20', 's7', 's21', 's8', 's12', 'op1', 'rul', 's17', 's13', 's11', 's4',
                                            'op2', 'op3', 's2', 's9', 's14', 's15', 'rul_clipped'])

    df_sensors = df_sensors.drop(columns=['op2', 'op3', 'op1', 'rul_clipped'])

    df_equipment['name'] = 'Turbofan №'+ df_equipment['unit'].astype(str)
    df_equipment['type'] = 'turbofan'
    df_equipment['dataset'] = 'FD001'
    df_equipment['unit_number'] = df_equipment['unit']
    df_equipment['install_date'] = date(2024, 1, 1)
    df_equipment['last_maintenance_date'] = date(2026, 2, 3)

    df_equipment = df_equipment.drop('unit', axis=1)
    df_equipment = df_equipment.drop('cycle', axis=1)

    df_equipment = df_equipment.drop_duplicates()
    dict_eq = df_equipment.to_dict('records')

    metadata = MetaData()
    sensor_readings = Table('sensor_readings', metadata, autoload_with=engine)
    equipment = Table('equipment', metadata, autoload_with=engine)


    try:
        with engine.connect() as connection:
            eq_insert = insert(equipment).values(dict_eq)
            eq_do_nothing = eq_insert.on_conflict_do_nothing()
            connection.execute(eq_do_nothing)

            max_cycle = df_sensors['cycle'].max()
            result = connection.execute(text('SELECT unit_number, id FROM equipment'))
            unit_to_id = dict(result.all())
            df_sensors['equipment_id'] = df_sensors['unit'].map(unit_to_id)
            df_sensors = df_sensors.drop('unit', axis=1)

            last_cycle = connection.execute(text('SELECT max(cycle) FROM sensor_readings')).scalar()

            if last_cycle is None:
                start_cycle = 1
            else:
                start_cycle = last_cycle + 1

            for cycle in range(start_cycle, max_cycle + 1):
                df_sensors_cycle = df_sensors[df_sensors['cycle'] == cycle]
                dict_sensors_cycle = df_sensors_cycle.to_dict('records')
                t0 = time.perf_counter()
                connection.execute(insert(sensor_readings).on_conflict_do_nothing(), dict_sensors_cycle)
                connection.commit()
                elapsed_ms = (time.perf_counter() - t0) * 1000
                logger.info("cycle %d: inserted %d rows in %.1f ms", cycle, len(dict_sensors_cycle), elapsed_ms)
                time.sleep(INTERVAL_SEC)
    except KeyboardInterrupt:
        logger.warning("interrupted by user")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    fill_db()