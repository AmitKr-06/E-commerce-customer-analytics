import pandas as pd
import pytest

from src.exception import CustomException
from src.utils import days_between, load_parquet, save_parquet


def test_days_between():
    a = pd.Series(pd.to_datetime(["2018-01-03 12:00:00"]))
    b = pd.Series(pd.to_datetime(["2018-01-01 00:00:00"]))
    assert days_between(1, b).iloc[0] == pytest.approx(2.5)


def test_parquet_roundtrip(tmp_path):
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    save_parquet(df, tmp_path / "sub" / "t.parquet")
    pd.testing.assert_frame_equal(load_parquet(tmp_path / "sub" / "t.parquet"), df)


def test_load_parquet_missing_file(tmp_path):
    with pytest.raises(CustomException):
        load_parquet(tmp_path / "nope.parquet")