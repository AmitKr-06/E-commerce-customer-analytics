import pandas as pd
from src.components.data_transformation import build_payments, clean_orders


def test_clean_orders_late_flag(orders_raw):
    o = clean_orders(orders_raw)
    assert o["is_late"].iloc[0] == 0         # delivered 9 days early
    assert o["is_late"].iloc[1] == 1         # delivered 5 days late
    assert pd.isna(o["is_late"].iloc[2])     # canceled: not in delivery analysis
    assert o["in_delivery_analysis"].tolist() ==[True, True, False]


def test_clean_orders_delivery_days(orders_raw):
    o = clean_orders(orders_raw)
    assert o["delivery_dyas"].iloc[0] == 10
    assert o["estimated_days"].iloc[0] == 19
    assert not o["flag_extreme_delivery"].any()


def test_clean_orders_does_not_change_row_count(orders_raw):
    assert len(clean_orders(orders_raw)) == len(orders_raw)


def test_build_payments(payments_raw):
    p = build_payments(payments_raw).iloc[0]
    assert p["revenue"] == 40.0
    assert p["n_payments"] == 2
    assert p["max_installments"] == 2           # 0 was clipped to 1
    assert p["main_payment_type"] == "voucher"  # largest payment