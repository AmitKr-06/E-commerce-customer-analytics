"""MLflow seup shared by model evaluation and model registry.

Local by default (sqlite file from constants.MLFLOW_URI).
"""

import os
import mlflow

from dotenv import load_dotenv
from src.constants import MLFLOW_EXPERIMENT, MLFLOW_URI
from src.config import PROJECT_ROOT
from src.logger import get_logger

log = get_logger("mlflow_utils")
load_dotenv(PROJECT_ROOT / ".env", override=True)

def setup_mlflow(experiment = MLFLOW_EXPERIMENT):
    """Set the tracking URI (and experiment) once. Returns the URI used."""
    token = os.getenv("DAGSHUB_TOKEN")
    if token:
        owner = os.getenv("DAGSHUB_REPO_OWNER")
        repo = os.getenv("DAGSHUB_REPO_NAME")
        missing = [k for k, v in (("DAGSHUB_REPO_OWNER", owner), ("DAGSHUB_REPO_NAME", repo)) if not v]
        if missing:
            raise EnvironmentError(f"Missing in .env: {missing}")
        os.environ["MLFLOW_TRACKING_USERNAME"] = token
        os.environ["MLFLOW_TRACKING_PASSWORD"] = token
        uri = f"https://dagshub.com/{owner}/{repo}.mlflow"
    else:
        uri = MLFLOW_URI
    mlflow.set_tracking_uri(uri)
    if experiment:
        mlflow.set_experiment(experiment)
    log.info("MLflow tracking URI: %s", uri)       # no credentials in this URL
    return uri
