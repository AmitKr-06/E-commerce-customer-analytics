"""Data Ingestion: Read the Raw CSV files into DataFrames."""

import pandas as pd
from pathlib import Path

from src.config import RAW_DIR, RAW_FILES
from src.exception import CustomException
from src.logger import get_logger
from src.utils import timed

log = get_logger("data_ingestion")

def load_raw(raw_dir = RAW_DIR, files = RAW_FILES, tables = None):
    """Return {table name: DataFrame}.
    
    tables: optional list of names to load (for example skip 'geolocation', which has 1M rows).
    Columns keep the pandas defaults on purpose, so results match the notebooks exactly.
    """
    raw_dir = Path(raw_dir)
    wanted = list(files) if tables is None else list(tables)
    unknown = [t for t in wanted if t not in files]
    if unknown:
        raise CustomException(f"Unknown table name(s): {unknown}. Known: {list(files)}")
    missing = [files[t] for t in wanted if not (raw_dir / files[t]).exists()]
    if missing:
        raise CustomException(f"Missing files in {raw_dir}: {missing}")

    data = {}
    with timed("raw data ingestion"):
        for name in wanted:
            try:
                data[name] = pd.read_csv(raw_dir / files[name])
            except Exception as e:
                raise CustomException(e) from e
            log.info("loaded %-12s %10s rows x %d columns", name, f"{len(data[name]):,}", data[name].shape[1])
    return data


if __name__ == "__main__":
    load_raw()