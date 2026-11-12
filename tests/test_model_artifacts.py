import numpy as np
import pandas as pd
import pytest

from src.config import MODELS_DIR
from src.constants import FEATURES, FEATURES_CAT, FEATURES_NUM, MODEL_FILE
from src.utils import load_object

MODEL_PATH = MODELS_DIR / MODEL_FILE
pytestmark = pytest.mark.skipif(not MODEL_PATH.exists(), reason="trained model not available")


@pytest.fixture(scope="module")
def bundle():
    return load_object(MODEL_PATH)

def test_bundle_content(bundle):
    assert {"model", "features", "categories", "trained_on"} <= set(bundle)
    assert bundle["features"] == FEATURES


def test_prediction_is_reasonable(bundle):
    row = {c: 1.0 for c in FEATURES_NUM}
    row.update(est_days = 20.0, distance_km = 400.0, n_items = 1)
    for c in FEATURES_CAT:
        row[c] = bundle["categories"][c][0]
    X = pd.DataFrame([row])[FEATURES]
    for c in FEATURES_CAT:
        X[c] = pd.Categorical(X[c], categories=bundle["categories"][c])
    pred = bundle["model"].predict(X)[0]
    assert np.isfinite(pred) and 0 < pred < 100


def test_missing_values_are_accepted(bundle):
    row = {c: np.nan for c in FEATURES_NUM}
    row["est_days"] = 20.0
    for c in FEATURES_CAT:
        row[c] = np.nan
    X = pd.DataFrame([row])[FEATURES]
    for c in FEATURES_CAT:
        X[c] = pd.Categorical(X[c], categories=bundle["categories"][c])
    assert np.isfinite(bundle["model"].predict(X)[0])