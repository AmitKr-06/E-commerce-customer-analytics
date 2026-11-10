"""Small helpers shared across the project."""
import random
import time
from contextlib import contextmanager
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.constants import SECONDS_PER_DAY
from src.exception import CustomException
from src.logger import get_logger

log = get_logger("utils")

def set_seed(seed = 42):
    random.seed(seed)
    np.random.seed(seed)


@contextmanager
def timed(label):
    """With timed('cleaning'): ... logs how long the block took."""
    start = time.time()
    yield
    log.info("%s finished in %.1fs", label, time.time() - start)


def days_between(later, earlier):
    """Difference of two datetime Series in days (float)."""
    return (later - earlier).dt.total_seconds() / SECONDS_PER_DAY

def save_parquet(df, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index = False)
    log.info("saved %s %s", path.name, df.shape)


def load_parquet(path):
    path = Path(path)
    if not path.exists():
        raise CustomException(f"File not found: {path}")
    return pd.read_parquet(path)

def save_object(obj, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok= True)
    joblib.dump(obj, path)
    log.info("saved object %s", path.name)


def load_object(path):
    path = Path(path)
    if not path.exists():
        raise CustomException(f"File not found: {path}")
    return joblib.load(path)
