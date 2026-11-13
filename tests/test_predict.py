import pandas as pd
import numpy as np
import pytest

from src.config import GEO_ZIP_FILE, MODELS_DIR
from src.constants import FEATURES, FEATURES_CAT, MODEL_FILE
from src.exception import CustomException
from src.model.model_prediction import Predictor

pytestmaker = pytest.mark.skipif(
    not ((MODELS_DIR / MODEL_FILE).exists() and GEO_ZIP_FILE.exists()),
    reason="trained model or geo_zip.parquet not available"
)

ORDER = {"est_days": 20, "customer_zip": 1037, "seller_zip": 1046, "customer_state": "SP",
         "seller_state": "SP", "main_category": "beleza_saude", "n_items": 1,
         "items_price": 80.0, "freight": 15.0, "weight_g": 500,
         "purchase_datetime": "2018-06-10 14:30:00"}


@pytest.fixture(scope="module")
def predictor():
    return Predictor()


def test_build_features_format(predictor):
    X, warnings, purchase = predictor.build_features(ORDER)
    assert list(X.columns) == FEATURES and len(X) == 1
    assert all(str(X[c].dtype) == "category" for c in FEATURES_CAT)
    assert X.at[0, "purchase_weekday"] == 6 and X.at[0, "purchase_hour"] == 14     # a Sunday, 14th
    assert warnings == []


def test_predict_output(predictor):
    out = predictor.predict(ORDER)
    assert 0 < out["predicted_days"] < 100
    assert out["predicted_delivery_date"] > "2018-06-10"
    assert out["platform_estimate_days"] == 20.0


def test_unknown_zip_gives_warning_not_crash(predictor):
    out = predictor.predict({**ORDER, "customer_zip": 99999999})
    assert any("zip" in w for w in out["warnings"])
    assert np.isfinite(out["predicted_days"])


def test_unknown_category_gives_warning(predictor):
    out = predictor.predict({**ORDER, "main_category": "not_a_category"})
    assert any("main_category" in w for w in out["warnings"])


def test_far_orders_take_longer(predictor):
    near = predictor.predict(ORDER)["predicted_days"]
    far = predictor.predict({**ORDER, "customer_zip": 69900, "customer_state": "AC"})["predicted_days"]
    assert far > near                   # Acre is far from Sao Paulo


def test_missing_est_days_raises(predictor):
    bad = {k: v for k, v in ORDER.items() if k != "est_days"}
    with pytest.raises(CustomException):
        predictor.predict(bad)
        