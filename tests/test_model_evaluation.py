from src.constants import EXPECTED_TRAINING, ROLLING_FOLDS, TEST_START, VALID_START
from src.model.model_evaluation import _decimals, check_expected


def _perfect_metrics():
    return {k: (v[0] if isinstance(v, tuple) else v) for k, v in EXPECTED_TRAINING.items()}


def test_decimals():
    assert _decimals(12.67) == 2
    assert _decimals(0.062) == 3


def test_check_expected_all_pass():
    assert check_expected(_perfect_metrics())["passed"].all()

def test_check_expected_detects_bad_metric():
    m = _perfect_metrics()
    m["test_model_mae"] = 9.0             # far outside 3.72  +/- 0.10
    report = check_expected(m)
    assert not report["passed"].all()


def test_check_expected_missing_metric_fails():
    m = _perfect_metrics()
    m.pop("cv_mean_mae")
    assert not check_expected(m)["passed"].all()


def test_split_dates_are_consistent():
    assert VALID_START < TEST_START
    assert all(end <= TEST_START for _, end in ROLLING_FOLDS)   # CV never touches test