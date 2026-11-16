"""Download the registered model bundle from the MLflow registry into models/ (used by CD)."""
import mlflow

from src.config import MODELS_DIR
from src.constants import MODEL_FILE, MODEL_NAME, PRODUCTION_ALIAS
from src.logger import get_logger
from src.mlflow_utils import setup_mlflow

log = get_logger("fetch_model")


def fetch_model(alias: str = PRODUCTION_ALIAS):
    client = mlflow.tracking.MlflowClient()
    mv = client.get_model_version_by_alias(MODEL_NAME, alias)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = client.download_artifacts(mv.run_id, MODEL_FILE, str(MODELS_DIR))
    log.info("model %s version %s (alias '%s') downloaded to %s", MODEL_NAME, mv.version, alias, path)
    return path


if __name__ == "__main__":
    setup_mlflow(experiment=None)
    fetch_model()