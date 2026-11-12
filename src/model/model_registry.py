"""Model Registry: Register the evaluated model in the MLflow Model Registry and alias it 'staging'."""

import json
import mlflow
import argparse
from mlflow.exceptions import MlflowException

from src.constants import MODEL_NAME, STAGING_ALIAS, PRODUCTION_ALIAS
from src.model.model_evaluation import EXPERIMENT_INFO_FILE
from src.exception import CustomException
from src.logger import get_logger
from src.mlflow_utils import setup_mlflow


log = get_logger("model_registry")


def load_model_info(file_path) -> dict:
    """Load the model info (run_id, model_path, checks_passed) from a JSON file."""
    try:
        with open(file_path, "r") as file:
            model_info = json.load(file)
        log.debug("Model info loaded from %s", file_path)
        return model_info
    except FileNotFoundError:
        log.error("File not found: %s", file_path)
        raise
    except Exception as e:
        log.error("Unexpected error occurred while loading the model info: %s", e)
        raise


def register_model(model_name: str, model_info: dict):
    """Register the model version and set the 'staging' alias."""
    try:
        if not model_info.get("checks_passed", False):
            raise CustomException("evaluation checks did not pass: model is not registered")

        client = mlflow.tracking.MlflowClient()
        try:
            client.create_registered_model(model_name)
        except MlflowException:
            pass                   # already exists

        source = f"runs:/{model_info['run_id']}/{model_info['model_path']}"
        model_version = client.create_model_version(name=model_name, source=source, run_id=model_info["run_id"])
        client.set_registered_model_alias(name=model_name, alias=STAGING_ALIAS, version=model_version.version)
        log.info('Model %s version %s registered and aliased as "%s".', model_name, model_version.version, STAGING_ALIAS)
        return model_version
    except CustomException:
        raise
    except Exception as e:
        log.error("Error during model registration: %s", e)
        raise


def promote_to_production(model_name: str, version: str = None):
    """Point the 'production' alias at the staging version (or at a given version, e.g. a rollback)."""
    try:
        client = mlflow.tracking.MlflowClient()
        if version is None:
            mv = client.get_model_version_by_alias(model_name, STAGING_ALIAS)
            version = mv.version
        else:
            mv = client.get_model_version(model_name, str(version))

        # guard: only promote versions whose evalution checks passed
        tags = client.get_run(mv.run_id).data.tags
        if tags.get("check_passed") != "True":
            raise CustomException(f"version {version} did not pass evaluation checks: not promoted")

        client.set_registered_model_alias(name=model_name, alias=PRODUCTION_ALIAS, version=str(version))
        log.info('Model %s version %s aliased as "%s".', model_name, version, PRODUCTION_ALIAS)
    except CustomException:
        raise
    except Exception as e:
        log.error("Error during model promotion: %s", e)
        raise



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--promote", action="store_true", help="move the 'production' alias")
    parser.add_argument("--version", default=None, help="with --promote: a specific version (rollback)")
    args = parser.parse_args()
    try:
        setup_mlflow(experiment=None)
        if args.promote:
            promote_to_production(MODEL_NAME, args.version)
        else:
            register_model(MODEL_NAME, load_model_info(EXPERIMENT_INFO_FILE))
    except Exception as e:
        log.error("Failed to complete the model registry step: %s", e)
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()