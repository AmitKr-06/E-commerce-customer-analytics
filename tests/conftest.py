import pandas as pd
import pytest 

@pytest.fixture
def orders_raw():
    """3 orders: on time, late, canceled (never delivered)."""
    return pd.DataFrame({
        "order_id": ["o1", "o2", "o3"],
        "customer_id": ["c1", "c2", "c3"],
        "order_status": ["delivered", "delivered", "canceled"],
        "order_purchase_timestamp": ["2018-01-01 10:00:00"] * 3,
        "order_approved_at": ["2018-01-01 11:00:00"] * 3,
        "order_delivered_carrier_date": ["2018-01-02 10:00:00", "2018-01-02 10:00:00", None],
        "order_delivered_customer_date": ["2018-01-11 10:00:00", "2018-01-25 10:00:00", None],
        "order_estimated_delivery_date": ["2018-01-20 10:00:00"] * 3,
    })


@pytest.fixture
def payments_raw():
    return pd.DataFrame({
        "order_id": ["o1", "o1"],
        "payment_sequential": [1, 2],
        "payment_type": ["credit_card", "voucher"],
        "payment_installments": [0, 2],
        "payment_value": [10.0, 30.0],
    })

