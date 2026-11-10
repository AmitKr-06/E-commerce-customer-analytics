"""Data Transfromation: Turn the raw tables into the analysis-ready datasets."""

import pandas as pd
import numpy as np

from pathlib import Path
from src.config import PROCESSED_DIR
from src.constants import (BRAZIL_LAT, BRAZIL_LNG, EXTRA_TRANSLATIONS, EXTREME_DELIVERY_DAYS,
                           INVALID_SALE_STATUSES, TREND_END, TREND_START)
from src.exception import CustomException
from src.logger import get_logger
from src.utils import days_between, save_parquet, timed
from src.components.data_ingestion import load_raw
from src.components.data_validation import validate_clean

log = get_logger("data_transformation")

ORDER_DATE_COLS = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
                   "order_delivered_customer_date", "order_estimated_delivery_date"]

def clean_orders(orders_raw):
    """Dates, quality flags (rows are kept), delivery features, time features."""
    orders = orders_raw.copy()
    for c in ORDER_DATE_COLS:
        orders[c] = pd.to_datetime(orders[c])

    delivered = orders["order_status"] == "delivered"
    orders["flag_delivered_no_date"] = delivered & orders["order_delivered_customer_date"].isna()
    orders["flag_carrier_before_approval"] = orders["order_delivered_carrier_date"] < orders["order_approved_at"]
    orders["flag_carrier_before_purchase"] = orders["order_delivered_carrier_date"] < orders["order_purchase_timestamp"]
    orders["flag_delivered_before_carrier"] = orders["order_delivered_customer_date"] < orders["order_delivered_carrier_date"]
    orders["in_delivery_analysis"] = delivered & orders["order_delivered_customer_date"].notna()

    orders["delivery_days"] = days_between(orders["order_delivered_customer_date"], orders["order_purchase_timestamp"])
    orders["estimated_days"] = days_between(orders["order_estimated_delivery_date"], orders["order_purchase_timestamp"])
    orders["delay_days"] = days_between(orders["order_delivered_customer_date"], orders["order_estimated_delivery_date"])
    orders["is_late"] = (orders["delay_days"] > 0).astype("Int64").where(orders["in_delivery_analysis"])
    orders["flag_extreme_delivery"] = orders["delivery_days"] > EXTREME_DELIVERY_DAYS

    orders["purchase_month"] = orders["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    orders["purchase_year"] = orders["order_purchase_timestamp"].dt.year
    orders["purchase_dow"] = orders["order_purchase_timestamp"].dt.day_of_week
    orders["purchase_hour"] = orders["order_purchase_timestamp"].dt.hour
    orders["in_trend_window"] = orders["purchase_month"].between(pd.Timestamp(TREND_START), pd.Timestamp(TREND_END))
    return orders


def build_payments(payments_raw):
    """One row per order: revenue, number of payments, max installments, main payment type."""
    pay = payments_raw.copy()
    pay["payment_installments"] = pay["payment_installments"].clip(lower = 1)  # 0 installments is impossible
    pay_order = pay.groupby("order_id").agg(
        revenue = ("payment_value", "sum"),
        n_payments = ("payment_sequential", "count"),
        max_installments = ("payment_installments", "max"),
    ).reset_index()
    main_type = (pay.sort_values(["order_id", "payment_value"], ascending = [True, False])
                 .drop_duplicates("order_id")[["order_id", "payment_type"]]
                 .rename(columns = {"payment_type": "main_payment_type"}))
    return pay_order.merge(main_type, on = "order_id", how = "left")


def build_items(items_raw):
    """Returns (items with a datetime shipping limit, one row per order)."""
    items = items_raw.copy()
    items["shipping_limit_date"] = pd.to_datetime(items["shipping_limit_date"])
    item_order = items.groupby("order_id").agg(
        n_items = ("order_item_id", "count"),
        n_products = ("product_id", "nunique"),
        n_sellers = ("seller_id", "nunique"),
        items_price = ("price", "sum"),
        freight_value = ("freight_value", "sum"),
    ).reset_index()
    item_order["items_total"] = item_order["items_price"] + item_order["freight_value"]
    return items, item_order


def build_reviews(reviews_raw):
    """Keep the latest review of each order."""
    rev = reviews_raw.copy()
    rev["review_creation_date"] = pd.to_datetime(rev["review_creation_date"])
    rev["review_answer_timestamp"] = pd.to_datetime(rev["review_answer_timestamp"])
    rev = (rev.sort_values(["order_id", "review_answer_timestamp"])
              .drop_duplicates("order_id", keep="last"))
    rev["has_comment"] = rev["review_comment_message"].notna()
    return rev[["order_id", "review_id", "review_score", "has_comment",
                "review_creation_date", "review_answer_timestamp"]].reset_index(drop=True)


def build_geography(geo_raw, customers_raw, sellers_raw):
    """Median coordinates per zip prefix, attached to customers and sellers."""
    geo = geo_raw.copy()
    in_brazil = (geo["geolocation_lat"].between(*BRAZIL_LAT) & geo["geolocation_lng"].between(*BRAZIL_LNG))
    log.info("geolocation rows removed (outside Brazil): %d", int((~in_brazil).sum()))
    geo = geo[in_brazil]
    geo_zip = (geo.groupby("geolocation_zip_code_prefix").agg(lat = ("geolocation_lat", "median"),lng = ("geolocation_lng", "median"))
               .reset_index()
               .rename(columns = {"geolocation_zip_code_prefix": "zip_code_prefix"}))
    if not geo_zip["zip_code_prefix"].is_unique:
        raise CustomException("geo_zip has duplicate zip prefixes")

    customers_clean = (customers_raw.merge(geo_zip, left_on = "customer_zip_code_prefix", right_on = "zip_code_prefix", how = "left")
                       .drop(columns = "zip_code_prefix")
                       .rename(columns = {"lat": "customer_lat", "lng": "customer_lng"}))
    sellers_clean = (sellers_raw.merge(geo_zip, left_on ="seller_zip_code_prefix", right_on = "zip_code_prefix", how = "left")
                     .drop(columns = "zip_code_prefix")
                     .rename(columns = {"lat": "seller_lat", "lng": "seller_lng"}))
    if len(customers_clean) != len(customers_raw) or len(sellers_clean) != len(sellers_raw):
        raise CustomException("geography join changed the number of customers or sellers")
    return geo_zip, customers_clean, sellers_clean


def build_products(products_raw, translation_raw):
    """English category name (with 2 manual additions), 'unknown' for missing, volume feature."""
    prod = products_raw.rename(columns={"product_name_lenght": "product_name_length",
                                        "product_description_lenght": "product_description_length"})
    extra = pd.DataFrame({"product_category_name": list(EXTRA_TRANSLATIONS),
                          "product_category_name_english": list(EXTRA_TRANSLATIONS.values())})
    trans = pd.concat([translation_raw, extra], ignore_index=True)
    products_clean = prod.merge(trans, on = "product_category_name", how = "left")
    if len(products_clean) != len(prod):
        raise CustomException("translation join changed the number of products")
    products_clean["product_category_name"] = products_clean["product_category_name"].fillna("unknown")
    products_clean["product_category_name_english"] = products_clean["product_category_name_english"].fillna("unknown")
    products_clean.loc[products_clean["product_weight_g"] == 0, "product_weight_g"] = np.nan
    products_clean["product_volume_cm3"] = (products_clean["product_length_cm"] *
                                            products_clean["product_height_cm"] *
                                            products_clean["product_width_cm"])
    return products_clean


def build_order_tables(orders, customers_clean, pay_order, items, item_order,
                       reviews_clean, products_clean, sellers_clean):
    """Order-level table (with the valid-sale flag) and item-level table."""
    orders_clean = (orders.merge(customers_clean[["customer_id", "customer_unique_id", "customer_city",
                                                  "customer_state", "customer_zip_code_prefix"]], on = "customer_id", how = "left")
                    .merge(pay_order, on = "order_id", how = "left")
                    .merge(item_order, on = "order_id", how = "left")
                    .merge(reviews_clean[["order_id", "review_score", "has_comment"]], on = "order_id", how = "left"))
    orders_clean["has_items"] = orders_clean["n_items"].notna()
    orders_clean["has_payment"] = orders_clean["revenue"].notna()

    # a valid sale: not canceled/unavailable, has a payment, has items
    orders_clean["is_valid_sale"] = ((~orders_clean["order_status"].isin(INVALID_SALE_STATUSES))
                                    & orders_clean["has_payment"] & orders_clean["has_items"])
    items_clean = (items.merge(products_clean[["product_id", "product_category_name_english", "product_weight_g",
                                               "product_volume_cm3"]], on = "product_id", how = "left")
                                               .merge(sellers_clean[["seller_id", "seller_city", "seller_state"]], on = "seller_id", how = "left")
                                               .merge(orders_clean[["order_id", "customer_unique_id", "customer_state", "order_status",
                                                                    "order_purchase_timestamp", "order_estimated_delivery_date",
                                                                    "order_delivered_customer_date", "delivery_days", "delay_days",
                                                                    "is_late", "in_delivery_analysis", "purchase_month"]],
                                                                    on = "order_id", how = "left"))
    items_clean["item_total"] = items_clean["price"] + items_clean["freight_value"]
    return orders_clean, items_clean

def transform(data, validate = True, strict = True):
    """data: dict from load_raw. Returns the seven cleaned datasets."""
    try:
        with timed("transformation"):
            orders = clean_orders(data["orders"])
            pay_order = build_payments(data["payments"])
            items, item_order = build_items(data["order_items"])
            reviews_clean = build_reviews(data["reviews"])
            geo_zip, customers_clean, sellers_clean = build_geography(data["geolocation"], data["customers"], data["sellers"])
            products_clean = build_products(data["products"], data["translation"])
            orders_clean, items_clean = build_order_tables(orders, customers_clean, pay_order, items, item_order,
                                                           reviews_clean, products_clean, sellers_clean)

            if len(items_clean) != len(items):
                raise CustomException("item table changed the number of rows")
            if validate:
                validate_clean(orders_clean, strict = strict)
            return {"orders_clean": orders_clean, "items_clean": items_clean, "customers_clean": customers_clean,
                    "sellers_clean": sellers_clean, "products_clean": products_clean,
                    "reviews_clean": reviews_clean, "geo_zip": geo_zip}
    except CustomException:
        raise
    except Exception as e:
        raise CustomException(e) from e


def save_processed(outputs, out_dir = PROCESSED_DIR):
    """Write each dataset to <out_dir>/<name>.parquet. Run the parity check first."""
    for name, df in outputs.items():
        save_parquet(df, Path(out_dir) / f"{name}.parquet")


if __name__ == "__main__":
    out = transform(load_raw())
    for k, v in out.items():
        log.info("%-16s  %s", k, v.shape)
    