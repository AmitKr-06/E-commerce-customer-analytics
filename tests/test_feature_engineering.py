import numpy as np
import pandas as pd

from src.components.feature_engineering import haversine, score_rfm
from src.constants import FEATURES, FORBIDDEN_FEATURES, RFM_SEGMENTS


def test_haversine_same_point_is_zero():
    assert haversine(-23.55, -46.63, -23.55, -46.63) == 0


def test_haversine_sao_paulo_rio():
    d = haversine(-23.55, -46.63, -22.91, -43.17)
    assert 340 < d < 380             # about 357 km

def test_no_forbidden_feature_in_model():
    assert not (FORBIDDEN_FEATURES & set(FEATURES))


def _rfm():
    rfm = pd.DataFrame({
        "customer_unique_id": [f"c{i:03d}" for i in range(100)],
        "recency_days": np.arange(1, 101, dtype=float),     # row 0 = most recent
        "monetary": np.arange(110, 10, -1, dtype=float),    # row 0 = highest spend
        "frequency": 1,
    })
    rfm.loc[1, "frequency"] = 2    # recent repeat buyer
    rfm.loc[98, "frequency"] = 2   # old repeat buyer
    return rfm


def test_score_rfm_ranges_and_names():
    seg = score_rfm(_rfm())
    assert seg["R"].between(1, 5).all() and seg["M"].between(1, 5).all()
    assert set(seg["segment"]) <= set(RFM_SEGMENTS)


def test_score_rfm_rules():
    seg = score_rfm(_rfm())
    assert seg.loc[0, "segment"] == "Recent high spenders"
    assert seg.loc[1, "segment"] == "Champions"
    assert seg.loc[98, "segment"] == "Repeat but lapsing"
    assert seg.loc[99, "segment"] == "Lapsed low spenders"


def test_repeat_buyers_never_in_one_time_segments():
    seg = score_rfm(_rfm())
    repeat = seg[seg["frequency"] >= 2]["segment"]
    assert set(repeat) <= {"Champions", "Repeat but lapsing"}