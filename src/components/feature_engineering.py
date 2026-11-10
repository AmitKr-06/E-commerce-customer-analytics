"""Feature Engineering: features tables built from the cleaned datasets."""

import numpy as np
import pandas as pd

from src.components.data_ingestion import load_raw
from src.components.data_transformation import transform
from src.constants import (EXPECTED_MODEL, EXPECTED_SEGMENTS, FEATURES, FEATURES_CAT, FORBIDDEN_FEATURES,
                           RFM_QUANTILES, TARGET_DAYS, TARGET_LATE, TEST_START, VALID_START)
from src.exception import CustomException
from src.logger import get_logger
from src.components.data_validation import Check, run_checks

log = get_logger("feature_engineering")

EARTH_RADIUS_KM = 6371

def haversine(lat1, lng1, lat2, lng2):
    """Great-circle distance in km between two points (arrays or series)."""
    lat1, lng1, lat2, lng2 = map(np.radians, [lat1, lng1, lat2, lng2])
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2
    return EARTH_RADIUS_KM * 2 * np.arcsin(np.sqrt(a))


# -------------------------------------- delivery-time model --------------------------------------------
def build_model_dataset(orders_clean, items_clean, products_clean, sellers_clean, customers_clean):
    """One row per delivered valid order: features known at purchase time, tow targets, and the split."""
    try:
        if FORBIDDEN_FEATURES & set(FEATURES):
            raise CustomException(f"a feature is only known after delivery: {FORBIDDEN_FEATURES & set(FEATURES)}")
        delivered = orders_clean[orders_clean["is_valid_sale"] & orders_clean["in_delivery_analysis"]]
        it = items_clean.loc[items_clean["order_id"].isin(delivered["order_id"]),
                             ["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"]]
        it = it.merge(products_clean[["product_id", "product_category_name", "product_weight_g",
                                      "product_volume_cm3"]], on = "product_id", how = "left")
        it["product_category_name"] = it["product_category_name"].replace("unknown", np.nan)
        agg = it.groupby("order_id").agg(n_items = ("order_item_id", "count"), n_sellers = ("seller_id", "nunique"),
                                         items_price = ("price", "sum"), freight = ("freight_value", "sum"))
        w = it.groupby("order_id")["product_weight_g"].agg(["sum", "count"])
        agg["weight_g"] = w["sum"].where(w["count"] > 0)              # empty when no item has a weight

        # main item = highest price, ties broken by item number
        main = (it.sort_values(["order_id", "price", "order_item_id"], ascending = [True, False, True])
                .drop_duplicates("order_id").set_index("order_id")
                [["seller_id", "product_category_name", "product_volume_cm3"]]
                .rename(columns = {"seller_id": "main_seller", "product_category_name": "main_category",
                                   "product_volume_cm3": "main_volume_cm3"}))
        agg = agg.join(main).reset_index()

        d = (delivered[["order_id", "customer_id", "customer_state", "order_purchase_timestamp",
                        "order_delivered_customer_date", "order_estimated_delivery_date"]]
                        .merge(customers_clean[["customer_id", "customer_lat", "customer_lng"]], on = "customer_id", how = "left")
                        .merge(agg, on = "order_id", how = "inner")
                        .merge(sellers_clean[["seller_id", "seller_state", "seller_lat", "seller_lng"]]
                               .rename(columns = {"seller_id": "main_seller"}), on = "main_seller", how = "inner"))

        day = pd.Timedelta(days=1)
        d["distance_km"] = haversine(d["customer_lat"], d["customer_lng"], d["seller_lat"], d["seller_lng"])
        d["est_days"] = (d["order_estimated_delivery_date"] - d["order_purchase_timestamp"]) / day
        d["purchase_month"] = d["order_purchase_timestamp"].dt.month
        d["purchase_weekday"] = d["order_purchase_timestamp"].dt.day_of_week
        d["purchase_hour"] = d["order_purchase_timestamp"].dt.hour
        d[TARGET_DAYS] = (d["order_delivered_customer_date"] - d["order_purchase_timestamp"]) / day
        d[TARGET_LATE] = d["order_delivered_customer_date"] > d["order_estimated_delivery_date"]

        t = d["order_purchase_timestamp"]
        d["split"] = np.where(t < VALID_START, "train", np.where(t < TEST_START, "valid", "test"))
        for c in FEATURES_CAT:
            d[c] = d[c].astype("category")
        return d[["order_id", "order_purchase_timestamp"] + FEATURES + [TARGET_DAYS, TARGET_LATE, "split"]]
    except CustomException:
        raise
    except Exception as e:
        raise CustomException(e) from e


def validate_model_data(d, strict = True):
    """Reconcile the model dataset."""
    E = EXPECTED_MODEL
    sizes = d["split"].value_counts().to_dict()
    checks = [
        Check("model rows", len(d) == E["rows"], f"{len(d):,} (expected {E['rows']:,})"),
        Check("late rate %", round(d[TARGET_LATE].mean() * 100, 2) == E["late_rate_pct"], f"{d[TARGET_LATE].mean() * 100:.2f} (expected {E['late_rate_pct']})"),
        Check("mean delivery days", round(d[TARGET_DAYS].mean(), 2) == E["mean_total_days"], f"{d[TARGET_DAYS].mean():.2f} (expected {E['mean_total_days']})"),
        Check("mean estimated days", round(d["est_days"].mean(), 2) == E["mean_est_days"], f"{d['est_days'].mean():.2f} (expected {E['mean_est_days']})"),
        Check("split sizes", all(sizes.get(k) == v for k, v in E["split_sizes"].items()), f"{sizes} (expected {E['split_sizes']})"),
        Check("missing distance", int(d["distance_km"].isna().sum()) == E["missing_distance"], f"{int(d['distance_km'].isna().sum())} (expected {E['missing_distance']})"),
        Check("missing main category", int(d["main_category"].isna().sum()) == E["missing_category"], f"{int(d['main_category'].isna().sum())} (expected {E['missing_category']})"),
        Check("max distance km", round(float(d["distance_km"].max()), 1) == E["max_distance_km"], f"{d['distance_km'].max():.1f} (expected {E['max_distance_km']})"),
        Check("no feature known only after delivery", not (FORBIDDEN_FEATURES & set(FEATURES))),
    ]
    return run_checks(checks, strict)

# --------------------------------------- RFM ----------------------------------------------------------------------------------------------------------------------------------------
def build_rfm(orders_clean):
    """One row per customer_unique_id from valid sales: first/last pruchase, frequency, monetary, recency."""
    valid = orders_clean.loc[orders_clean["is_valid_sale"], ["order_id", "customer_unique_id",
                                                             "order_purchase_timestamp", "revenue"]]
    rfm = valid.groupby("customer_unique_id").agg(
        first_purchase=("order_purchase_timestamp", "min"),
        last_purchase=("order_purchase_timestamp", "max"),
        frequency=("order_id", "count"),
        monetary=("revenue", "sum"),
    ).reset_index()                                              # sorted by customer id: repeatable ties
    rfm["monetary"] = rfm["monetary"].astype(float).round(2)     # same values as MySQL DECIMAL sums
    ref_date = rfm["last_purchase"].max().normalize() + pd.Timedelta(days=1)
    rfm["recency_days"] = (ref_date - rfm["last_purchase"]).dt.total_seconds() / 86400
    rfm.attrs["reference_date"] = ref_date
    return rfm

def score_rfm(rfm):
    """R and M in quintiles (5 = best), f in fixed bands, then rule-based segments (first match wins)."""
    labels = list(range(1, RFM_QUANTILES + 1))
    out = rfm.copy()
    out["R"] = pd.qcut(out["recency_days"].rank(method="first", ascending=False), RFM_QUANTILES, labels=labels).astype(int)
    out["M"] = pd.qcut(out["monetary"].rank(method="first"), RFM_QUANTILES, labels=labels).astype(int)
    out["F"] = np.select([out["frequency"] == 1, out["frequency"] == 2], [1, 2], default=3)
    conds = [
        (out["F"] >= 2) & (out["R"] >= 4),     # repeat buyers who ordered recently
        (out["F"] >= 2),                       # repeat buyers who have gone quiet
        (out["R"] >= 4) & (out["M"] >= 4),     # one order, recent, high spend
        (out["R"] >= 4),                       # one order, recent
        (out["M"] >= 4),                       # one order, not recent, high spend
    ]
    names = ["Champions", "Repeat but lapsing", "Recent high spenders", "Recent customers", "Lapsed high spenders"]
    out["segment"] = np.select(conds, names, default="Lapsed low spenders")
    out.attrs.update(rfm.attrs)
    return out

def build_segments(orders_clean):
    return score_rfm(build_rfm(orders_clean))

def validate_segments(seg, strict = True):
    sizes = seg["segment"].value_counts().to_dict()
    checks = [Check(f"segment: {k}", sizes.get(k) == v, f"{sizes.get(k)} (expected {v:,})") for k, v in EXPECTED_SEGMENTS.items()]
    return run_checks(checks, strict)


if __name__ == "__main__":
    out = transform(load_raw())
    model_data = build_model_dataset(out["orders_clean"], out["items_clean"], out["products_clean"],
                                     out["sellers_clean"], out["customers_clean"])
    log.info("model dataset %s", model_data.shape)
    validate_model_data(model_data, strict=False)
    seg = build_segments(out["orders_clean"])
    log.info("segments %s, refrence date %s", seg.shape, seg.attrs["reference_date"].date())
    validate_segments(seg, strict=False)