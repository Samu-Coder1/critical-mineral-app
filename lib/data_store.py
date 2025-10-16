import os
import pandas as pd
from datetime import datetime

class CSVStore:
    def __init__(self, path, id_field=None):
        self.path = path
        self.id_field = id_field

    def load(self):
        if os.path.exists(self.path):
            return pd.read_csv(self.path)
        return pd.DataFrame()

    def save(self, df):
        df.to_csv(self.path, index=False)

    def append_row(self, row_dict):
        df = self.load()
        df.loc[len(df)] = row_dict
        self.save(df)
        return df

    def delete_by_id(self, id_value):
        df = self.load()
        if self.id_field is None:
            return df
        df = df[df[self.id_field] != id_value]
        self.save(df)
        return df

    def next_id(self):
        df = self.load()
        if self.id_field and not df.empty:
            return int(df[self.id_field].max()) + 1
        return 1

# convenience helpers

def load_csv(path):
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()


def save_csv(df, path):
    df.to_csv(path, index=False)


def append_csv_row(path, row_dict):
    df = load_csv(path)
    df.loc[len(df)] = row_dict
    save_csv(df, path)
    return df
