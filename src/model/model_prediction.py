"""Prediction: Predicted delivery days (shared by the API and the tests)."""

import numpy as np
import pandas as pd

from src.components.feature_engineering import haversine
from src.config import GEO_ZIP_FILE, MODELS_DIR
from src.constants import FEATURES, FEATURES_CAT, MODEL_FILE
from src.exception import CustomException
from src.logger import get_logger
from src.utils import load_object, load_parquet

log = get_logger("model_prediction")


class Predictor:
    """Loads the saved regressor bundle and the zip-prefix coordinates once."""
    def __init__(self, model_path = MODELS_DIR / MODEL_FILE, geo_path =GEO_ZIP_FILE):
        bundle = load_object(model_path)
        self.model = bundle["model"]
        self.features = bundle["features"]
        self.categories = bundle["categories"]
        self.trained_on = bundle["trained_on"]
        geo = load_parquet(geo_path).set_index("zip_code_prefix")
        self.lat, self.lng = geo["lat"], geo["lng"]
        log.info("Predictor ready (%s)", self.trained_on)

    def distance_km(self, customer_zip, seller_zip) -> float:
        """Distance between the two zip-prefix centers; NaN when a prefix is unknown."""
        try:
            return float(haversine(self.lat[int(customer_zip)], self.lng[int(customer_zip)],
                                   self.lat[int(seller_zip)], self.lng[int(seller_zip)]))
        except (KeyError, TypeError, ValueError):
            return np.nan


    def build_features(self, order: dict):
        """One order dict -> (one-row DataFrame in training format, list of warnings)."""
        warnings  = []
        purchase = pd.Timestamp(order.get("purchase_datetime") or pd.Timestamp.now())

        distance = self.distance_km(order.get("customer_zip"), order.get("seller_zip"))
        if np.isnan(distance):
            warnings.append("zip prefix not found: distance is missing, the model handles it but is less exact")

        volume = order.get("main_volume_cm3")
        if volume is None and all(order.get(k) for k in ("length_cm", "height_cm", "width_cm")):
            volume = order["length_cm"] * order["height_cm"] * order["width_cm"]

        row = {
            "est_days": order["est_days"],
            "distance_km": distance,
            "n_items": order.get("n_items", 1),
            "n_sellers": order.get("n_sellers", 1),
            "items_price": order.get("items_price"),
            "freight": order.get("freight"),
            "weight_g": order.get("weight_g"),
            "main_volume_cm3": volume,
            "purchase_month": purchase.month,
            "purchase_weekday": purchase.dayofweek,
            "purchase_hour": purchase.hour,
            "customer_state": order.get("customer_state"),
            "seller_state": order.get("seller_state"),
            "main_category": order.get("main_category"),
        }
        X = pd.DataFrame([row])[FEATURES]
        for c in FEATURES_CAT:
            if X.at[0, c] is not None and X.at[0, c] not in set(self.categories[c]):
                warnings.append(f"{c} '{X.at[0, c]}' was not seen in training: treated as missing")
            X[c] = pd.Categorical(X[c], categories=self.categories[c])   # unseen -> NaN
        num_cols = [c for c in FEATURES if c not in FEATURES_CAT]
        X[num_cols] = X[num_cols].astype(float)
        return X, warnings, purchase


    def predict(self, order: dict) -> dict:
        try:
            X, warnings, purchase = self.build_features(order)
            days = max(float(self.model.predict(X)[0]), 0.0)
            return {
                "predicted_days": round(days, 1),
                "predicted_delivery_date": (purchase + pd.Timedelta(days=days)).date().isoformat(),
                "platform_estimate_days": float(order["est_days"]),
                "platform_minus_model_days": round(float(order["est_days"]) - days, 1),
                "model_trained_on": self.trained_on,
                "warnings": warnings,
            }
        except KeyError as e:
            raise CustomException(f"missing input field: {e}") from e
        except Exception as e:
            raise CustomException(e) from e


if __name__ == "__main__":
    sample_order = {
        "est_days": 20,                                # delivery estimate shown at purchase (days)
        "customer_zip": 1037, "customer_state": "SP",
        "seller_zip": 1046, "seller_state": "SP",
        "main_category": "beleza_saude",
        "n_items": 1, "n_sellers": 1,
        "items_price": 80.0, "freight": 15.0, "weight_g": 500,
        "purchase_datetime": "2018-06-10 14:30:00",
    }

    predictor = Predictor()
    result = predictor.predict(sample_order)

    for key, value in result.items():
        log.info("%-26s %s", key, value)