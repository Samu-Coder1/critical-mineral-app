import os
import pandas as pd
from datetime import datetime

def ensure_csv_header(path, header_line):
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(header_line + '\n')

def backup_file(path):
    base = path.rsplit('.',1)[0]
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    dest = f"{base}_{ts}.bak.csv"
    with open(path,'r',encoding='utf-8') as src, open(dest,'w',encoding='utf-8') as dst:
        dst.write(src.read())
    return dest

def load_csv(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def save_csv(df, path):
    df.to_csv(path, index=False)
