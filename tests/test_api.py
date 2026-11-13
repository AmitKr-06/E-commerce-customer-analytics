import pytest
from fastapi.testclient import TestClient

from src.config import GEO_ZIP_FILE, MODELS_DIR
from src.constants import MODEL_FILE

pytestmark = pytest.mark.skipif(
    not ((MODELS_DIR / MODEL_FILE).exists() and GEO_ZIP_FILE.exists()),
    reason="trained model or geo_zip.parquet not available")

ORDER = {"est_days": 20, "customer_zip": 1037, "seller_zip": 1046, "customer_state": "SP",
         "seller_state": "SP", "main_category": "beleza_saude", "items_price": 80.0,
         "freight": 15.0, "weight_g": 500, "purchase_datetime": "2018-06-10T14:30:00"}


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:         # "with" runs startup, which loads the model
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_home_page(client):
    r = client.get("/")
    assert r.status_code == 200 and "Delivery time estimator" in r.text


def test_predict_ok(client):
    r = client.post("/predict", json=ORDER)
    assert r.status_code == 200
    body = r.json()
    assert 0 < body["predicted_days"] < 100
    assert body["platform_estimate_days"] == 20.0


def test_predict_minimal_order(client):
    r = client.post("/predict", json={"est_days": 15, "customer_zip": 1037, "seller_zip": 1046})
    assert r.status_code == 200


def test_predict_rejects_bad_input(client):
    assert client.post("/predict", json={**ORDER, "est_days": -5}).status_code == 422
    assert client.post("/predict", json={"customer_zip": 1037}).status_code == 422
    assert client.post("/predict", json={**ORDER, "customer_zip": "abc"}).status_code == 422