from prepare_rul import add_rul, load_train
from datetime import date

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Table, MetaData, text
from sqlalchemy.dialects.postgresql import insert

import numpy as np
import pandas as pd
from pathlib import Path
import argparse

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
    load_dotenv()
    engine = create_engine(os.getenv("DATABASE_URL"))

    df_sensors = get_data()
    df_equipment = df_sensors.drop(columns=['s3', 's20', 's7', 's21', 's8', 's12', 'op1', 'rul', 'cycle', 's17', 's13', 's11', 's4',
                                            'op2', 'op3', 's2', 's9', 's14', 's15', 'rul_clipped'])

    df_sensors = df_sensors.drop(columns=['op2', 'op3', 'op1', 'rul_clipped'])

    df_equipment['name'] = 'Turbofan №'+ df_equipment['unit'].astype(str)
    df_equipment['type'] = 'turbofan'
    df_equipment['dataset'] = 'FD001'
    df_equipment['unit_number'] = df_equipment['unit']
    df_equipment['install_date'] = date(2024, 1, 1)
    df_equipment['last_maintenance_date'] = date(2026, 2, 3)

    df_equipment = df_equipment.drop('unit', axis=1)

    df_equipment = df_equipment.drop_duplicates()
    dict_eq = df_equipment.to_dict('records')

    metadata = MetaData()
    sensor_readings = Table('sensor_readings', metadata, autoload_with=engine)
    equipment = Table('equipment', metadata, autoload_with=engine)

    with engine.connect() as connection:
        eq_insert = insert(equipment).values(dict_eq)
        eq_do_nothing = eq_insert.on_conflict_do_nothing()
        connection.execute(eq_do_nothing)

        result = connection.execute(text('SELECT unit_number, id FROM equipment'))
        unit_to_id = dict(result.all())
        df_sensors['equipment_id'] = df_sensors['unit'].map(unit_to_id)
        df_sensors = df_sensors.drop('unit', axis=1)
        dict_sensors = df_sensors.to_dict('records')
        connection.execute(insert(sensor_readings).on_conflict_do_nothing(), dict_sensors)


        connection.commit()


if __name__ == "__main__":
    fill_db()