"""Model Building: Fit the delivery-time regressor (and the late-or-not classifier) and save them.

Final models are fitted on train + valid (purchase < TEST_START) with the settings fixed in notebook 11.
"""
import pandas as pd
import json

from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, roc_auc_score

from src.components.data_ingestion import load_raw
from src.components.data_transformation import transform
from src.components.feature_engineering import build_model_dataset, validate_model_data
from src.config import MODELS_DIR, MODEL_DATA_FILE, TRAIN_METRICS_FILE
from src.constants import (CLF_FILE, CLF_PARAMS, FEATURES, FEATURES_CAT, MODEL_FILE, REG_PARAMS,
                           ROLLING_FOLDS, TARGET_DAYS, TARGET_LATE)
from src.exception import CustomException
from src.logger import get_logger
from src.utils import save_object, save_parquet, set_seed, timed

log = get_logger("model_building")

def build_data() -> pd.DataFrame:
    """Raw CSV -> cleaned tables -> model dataset (one row per delivered valid order),
    validated.
    """
    try:
        out = transform(load_raw())
        d = build_model_dataset(out["orders_clean"], out["items_clean"], out["products_clean"],
                                out["sellers_clean"], out["customers_clean"])
        validate_model_data(d, strict=True)
        return d
    except Exception as e:
        log.error("Error while building the model dataset: %s", e)
        raise CustomException(e) from e


def split_data(d: pd.DataFrame):
    """dev = train + valid (fit), test = held out (evaluation only)."""
    dev = d[d["split"].isin(["train", "valid"])]
    test = d[d["split"] == "test"]
    log.info("dev %d rows | test %d rows", len(dev), len(test))
    return dev, test

def train_regressor(dev: pd.DataFrame) -> HistGradientBoostingRegressor:
    """Absolute-error gradient boosting for total delivery days."""
    try:
        reg = HistGradientBoostingRegressor(**REG_PARAMS).fit(dev[FEATURES], dev[TARGET_DAYS])
        log.info("Regressor training completed")
        return reg
    except Exception as e:
        log.error("Error during regressor training: %s", e)
        raise


def train_classifier(dev: pd.DataFrame) -> HistGradientBoostingClassifier:
    """Gradient boosting for 'late or not' (diagnostic; not reliable enough for alerts)."""
    try:
        clf = HistGradientBoostingClassifier(**CLF_PARAMS).fit(dev[FEATURES],
                                                               dev[TARGET_LATE].astype(int))
        log.info("Classifier training completed")
        return clf
    except Exception as e:
        log.error("Error during classifier training: %s", e)
        raise


def rolling_cv(dev: pd.DataFrame) -> pd.DataFrame:
    """Rolling-origin validation inside dev (3 folds, always train on the past). Test not used."""
    ts = dev["order_purchase_timestamp"]
    rows = []
    for start, end in ROLLING_FOLDS:
        tr, va = dev[ts < start], dev[(ts >= start) & (ts < end)]
        reg = HistGradientBoostingRegressor(**REG_PARAMS).fit(tr[FEATURES], tr[TARGET_DAYS])
        clf = HistGradientBoostingClassifier(**CLF_PARAMS).fit(tr[FEATURES],
                                                               tr[TARGET_LATE].astype(int))
        line = LinearRegression().fit(tr[["est_days"]], tr[TARGET_DAYS])
        rows.append({"valid_period": f"{start} to {end}",
                     "train_orders": len(tr), "valid_orders": len(va),
                     "MAE_model": mean_absolute_error(va[TARGET_DAYS], reg.predict(va[FEATURES])),
                     "MAE_line": mean_absolute_error(va[TARGET_DAYS], line.predict(va[["est_days"]])),
                     "AUROC_model": roc_auc_score(va[TARGET_LATE].astype(int),
                                                  clf.predict_proba(va[FEATURES])[:, 1]),
                                                  })
        cv = pd.DataFrame(rows).set_index("valid_period")
        log.info("rolling CV mean MAE %.3f | mean AUROC %3.f", cv["MAE_model"].mean(),
                 cv["AUROC_model"].mean())
        return cv


def save_train_metrics(cv: pd.DataFrame, trained_on: str, file_path=TRAIN_METRICS_FILE) -> None:
    """Save the CV summary so model_evaluation.py can log and check it."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok= True)
        info = {"cv_mean_mae": float(cv["MAE_model"].mean()),
                "cv_mean_auroc": float(cv["AUROC_model"].mean()),
                "cv_mean_mae_line": float(cv["MAE_line"].mean()),
                "trained_on": trained_on}
        with open(file_path, "w") as file:
            json.dump(info, file, indent=4)
        log.info("Train metrics saved to %s", file_path)
    except Exception as e:
        log.error("Error occurred while saving train metrics: %s", e)
        raise

def main():
    try:
        set_seed(42)
        with timed("model building"):
            d = build_data()
            save_parquet(d, MODEL_DATA_FILE)     # evaluation reads the same rows
            dev, _ = split_data(d)
            cv = rolling_cv(dev)
            reg = train_regressor(dev)
            clf = train_classifier(dev)

            trained_on = f"orders up to {dev['order_purchase_timestamp'].max().date()}"
            cats = {c: d[c].cat.categories for c in FEATURES_CAT}       # needed to encode new data

            save_object({"model": reg, "features": FEATURES, "categories": cats, "trained_on":trained_on}, MODELS_DIR / MODEL_FILE)
            save_object({"model": clf, "features": FEATURES, "categories": cats, "trained_on": trained_on}, MODELS_DIR / CLF_FILE)
            save_train_metrics(cv, trained_on)
    except Exception as e:
        log.error("Failed to complete the model building process: %s", e)
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()