"""Model Evaluation: score the saved models once on the test period, check the numbers, log to MLflow."""

import pandas as pd
import numpy as np
import json
import mlflow
import mlflow.sklearn
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, roc_auc_score

from src.components.data_validation import Check, run_checks
from src.model.model_building import split_data
from src.config import (MODELS_DIR, MODEL_DATA_FILE, TRAIN_METRICS_FILE,
                        METRICS_FILE, EXPERIMENT_INFO_FILE)
from src.constants import (CLF_FILE, EXPECTED_TRAINING, FEATURES, FEATURES_CAT, MODEL_FILE,
                           REG_PARAMS, TARGET_DAYS, TARGET_LATE)
from src.exception import CustomException
from src.logger import get_logger
from src.utils import load_object, load_parquet
from src.mlflow_utils import setup_mlflow

log = get_logger("model_evaluation")

def load_test_data(bundle: dict):
    """Load the model dataset and give the categorical columns the categories saved at training."""
    d = load_parquet(MODEL_DATA_FILE)
    for c in FEATURES_CAT:
        d[c] = pd.Categorical(d[c], categories=bundle["categories"][c])
    return split_data(d)


def evaluate_model(reg, clf, dev: pd.DataFrame, test: pd.DataFrame) -> dict:
    """Test-period metrics for the regressor, the baselines and the classifier."""
    try:
        y = test[TARGET_DAYS]
        y_late = test[TARGET_LATE].astype(int)
        line = LinearRegression().fit(dev[["est_days"]], dev[TARGET_DAYS])
        p_reg = reg.predict(test[FEATURES])
        p_clf = clf.predict_proba(test[FEATURES])[:, 1]

        metrics = {
            "test_platform_mae": mean_absolute_error(y, test["est_days"]),
            "test_line_mae": mean_absolute_error(y, line.predict(test[["est_days"]])),
            "test_model_mae": mean_absolute_error(y, p_reg),
            "test_model_median_abs_error": float(np.median(np.abs(y - p_reg))),
            "test_model_bias": float((p_reg - y).mean()),
            "test_auroc_est_days": roc_auc_score(y_late, -test["est_days"]),
            "test_model_auroc": roc_auc_score(y_late, p_clf),
            "test_late_rate": float(y_late.mean()),
        }
        log.info("Model evaluation metrics calculated")
        return {k: float(v) for k, v in metrics.items()}
    except Exception as e:
        log.error("Error during model Evaluation: %s", e)
        raise


def _decimals(x: float) -> int:
    s = str(x)
    return len(s.split(".")[1]) if "." in s else 0


def check_expected(metrics: dict) -> pd.DataFrame:
    """Compare with constants.EXPECTED_TRAINING: plain number = exact to its decimals, tuple = (value, tolerance)."""
    checks = []
    for name, exp in EXPECTED_TRAINING.items():
        got = metrics.get(name)
        if got is None:
            checks.append(Check(name, False, "metric not available"))
            continue
        if isinstance(exp, tuple):
            value, tol = exp
            ok, detail = abs(got - value) <= tol, f"{got:.3f} (expected {value} +/- {tol})"
        else:
            ok, detail = round(got, _decimals(exp)) == exp, f"{got:.4f} (expected {exp})"
        checks.append(Check(name, bool(ok), detail))
    return run_checks(checks, strict=False)


def save_json(obj: dict, file_path) -> None:
    try:
        file_path.parent.mkdir(parents = True, exist_ok = True)
        with open(file_path, "w") as file:
            json.dump(obj, file, indent=4)
        log.info("Saved %s", file_path)
    except Exception as e:
        log.error("Error occurred while saving %s: %s", file_path, e)
        raise


def main():
    setup_mlflow()
    with mlflow.start_run() as run:
        try:
            bundle = load_object(MODELS_DIR / MODEL_FILE)
            clf_bundle = load_object(MODELS_DIR / CLF_FILE)
            reg, clf = bundle["model"], clf_bundle["model"]
            dev, test = load_test_data(bundle)

            metrics = evaluate_model(reg, clf, dev, test)
            with open(TRAIN_METRICS_FILE) as f:
                train_info = json.load(f)
            metrics["cv_mean_mae"] = train_info["cv_mean_mae"]
            metrics["cv_mean_auroc"] = train_info["cv_mean_auroc"]

            report = check_expected(metrics)
            check_passed = bool(report["passed"].all())
            save_json(metrics, METRICS_FILE)

            # Log to MLflow
            for name, value in metrics.items():
                mlflow.log_metric(name, value)
            for name, value in REG_PARAMS.items():
                mlflow.log_param(name, value)
            mlflow.log_param("trained_on", bundle["trained_on"])
            mlflow.log_param("n_features", len(FEATURES))
            mlflow.set_tag("check_passed", str(check_passed))

            model_info = mlflow.sklearn.log_model(reg, name="model", serialization_format="cloudpickle")
            logging_id = getattr(model_info, "model_id", None)
            log.info("Model logged to MLflow successfully! Model ID: %s", logging_id)

            mlflow.log_artifact(str(MODELS_DIR / MODEL_FILE))    # bundle with feature list and categories
            mlflow.log_artifact(str(METRICS_FILE))

            # run_id + path for model_registry.py
            save_json({"run_id": run.info.run_id, "model_path": "model", "checks_passed": check_passed}, EXPERIMENT_INFO_FILE)
        except Exception as e:
            log.error("Failed to complete the model evalution process: %s", e)
            print(f"Error: {e}")
            raise CustomException(e) from e


if __name__ == "__main__":
    main()