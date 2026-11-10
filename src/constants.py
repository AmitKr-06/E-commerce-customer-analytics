"""Business rules, expected numbers, feature lists, split dates and model settings.

Paths and file names are in config.py. Change a rule here and every module follows.
"""
from .config import PROJECT_ROOT

# ------------------------- raw data ------------------------------------------------
EXPECTED_ROWS = {
    "customers": 99441, "geolocation": 1000163, "order_items": 112650, "payments": 103886,
    "reviews": 99224, "orders": 99441, "products": 32951, "sellers": 3095, "translation": 71,
}

REQUIRED_COLUMNS = {
    "customers": ["customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city", "customer_state"],
    "geolocation": ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng", "geolocation_city", "geolocation_state"],
    "order_items": ["order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date", "price", "freight_value"],
    "payments": ["order_id", "payment_sequential", "payment_type", "payment_installments", "payment_value"],
    "reviews": ["review_id", "order_id", "review_score", "review_comment_title", "review_comment_message",
                "review_creation_date", "review_answer_timestamp"],
    "orders": ["order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at",
               "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"],
    "products": ["product_id", "product_category_name", "product_name_lenght", "product_description_lenght",
                 "product_photos_qty", "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"],
    "sellers": ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    "translation": ["product_category_name", "product_category_name_english"],
}

# table -> columns must be unique together
UNIQUE_KEYS = {
    "customers": ["customer_id"], "orders": ["order_id"], "products": ["product_id"], "sellers": ["seller_id"],
    "order_items": ["order_id", "order_item_id"], "payments": ["order_id", "payment_sequential"],
    "translation": ["product_category_name"],
}

ORDER_STATUSES = {"delivered", "shipped", "canceled", "unavailable", "invoiced", "processing", "created", "approved"}

# ------------------------------- Business rules ----------------------------------------------------------------------
SECONDS_PER_DAY = 86400
INVALID_SALE_STATUSES = ("canceled", "unavailable")   # never counted as a sale
EXTREME_DELIVERY_DAYS = 60                            # flagged, not removed
TREND_START, TREND_END = "2017-01-01", "2018-08-01"   # months outside are incomplete
BRAZIL_LAT, BRAZIL_LNG = (-34, 5.3), (-74, -34)
EXTRA_TRANSLATIONS = {                                # categories missing an English name
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_food_preparers",
    "pc_gamer": "pc_gamer",
}

# ------------------------------- Numbers every run must reproduce ------------------------------------------------------
EXPECTED = {
    "valid_orders": 98198,
    "customers": 94982,
    "revenue": 15738221.95,
    "repeat_customers": 2887,
    "deliverred_valid_orders": 96469,
}

REVENUE_TOLERANCE = 0.01   # R$

# ---------------------------------- RFM -----------------------------------------------------------------------------------
RFM_QUANTILES = 5
RFM_SEGMENTS = ["Champions", "Repeat but lapsing", "Recent high spenders",
                "Recent customers", "Lapsed high spenders", "Lapsed low spenders"]


# ---------------------------------- Delivery-time mmodel ------------------------------------------------------------------
TARGET_DAYS, TARGET_LATE = "total_days", "is_late"
FEATURES_NUM = ["est_days", "distance_km", "n_items", "n_sellers", "items_price","freight", "weight_g",
                "main_volume_cm3", "purchase_month", "purchase_weekday", "purchase_hour"]

FEATURES_CAT = ["customer_state", "seller_state", "main_category"]
FEATURES = FEATURES_NUM + FEATURES_CAT

VALID_START, TEST_START = "2018-03-01", "2018-05-01"        # train < VALID_START <= valid < TEST_START <= test
ROLLING_FOLDS = [("2017-11-01", "2018-01-01"), ("2018-01-01", "2018-03-01"), ("2018-03-01", "2018-05-01")]

# Exact Parameters to train Regression Model
REG_PARAMS = dict(loss = "absolute_error", learning_rate = 0.1, max_leaf_nodes = 15, max_iter = 300,
                  min_samples_leaf = 50, categorical_features = "from_dtype", random_state = 42)

RANDOM_STATE = 42

# --------------------------------------- Experiment tracking --------------------------------------------------------------
MLFLOW_EXPERIMENT = "delivery-time-regression"
MLFLOW_URI = f"sqlite:///{(PROJECT_ROOT / 'mlflow.db').as_posix()}"