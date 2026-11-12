import pandas as pd
import pytest

from src.components.data_validation import Check, run_checks, validate_clean
from src.exception import CustomException


def test_run_checks_strict_raises():
    with pytest.raises(CustomException):
        run_checks([Check("bad", False)], strict=True)


def test_run_checks_not_strict_returns_report():
    report = run_checks([Check("ok", True), Check("bad", False)], strict=False)
    assert report["passed"].tolist() == [True, False]


def test_validate_clean_missing_columns():
    with pytest.raises(CustomException):
        validate_clean(pd.DataFrame({"order_id": ["o1"]}))


def test_validate_clean_wrong_numbers_fail():
    df = pd.DataFrame({"order_id": ["o1"], "customer_unique_id": ["u1"], "revenue": [10.0],
                       "is_valid_sale": [True], "in_delivery_analysis": [True]})
    with pytest.raises(CustomException):
        validate_clean(df, strict=True)