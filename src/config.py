"""Project paths, file names and constants shared by notebooks and scripts."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SQL_DIR = PROJECT_ROOT / "sql"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIG_DIR = REPORTS_DIR / "figures"   

# logical table name -> file in data/raw/
RAW_FILES = {
    "customers":   "customers.csv",
    "geolocation": "geolocation.csv",
    "order_items": "order_items.csv",
    "payments":    "order_payments.csv",
    "reviews":     "order_review.csv",
    "orders":      "orders.csv",
    "products":    "products.csv",
    "sellers":     "sellers.csv",
    "translation": "product_category_name.csv",
}

# Analysis window used for trend charts (months incomplete outside it)
TREND_START = "2017-01-01"
TREND_END = "2018-08-01"

# The two categories with no English name in the raw translation file 
EXTRA_TRANSLATIONS = {
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_food_preparers",
    "pc_gamer": "pc_gamer",
}

# Bounding box of Brazil used to drop bad geolocation points
BRAZIL_LAT = (-34, 5.3)
BRAZIL_LNG = (-74, -34)

# Relocation numbers every notebook must reproduce
EXPECTED = {
    "valid_orders": 98198,
    "customers": 94982,
    "revenue": 15738221.95,
    "repeat_customers": 2887,
    "delivered_valid_orders": 96469
}

# the model pipeline
MODEL_DATA_FILE = PROCESSED_DIR / "model_dataset.parquet"
TRAIN_METRICS_FILE = REPORTS_DIR / "train_metrics.json"
METRICS_FILE = REPORTS_DIR / "metrics.json"
EXPERIMENT_INFO_FILE = REPORTS_DIR / "experiment_info.json"

GEO_ZIP_FILE = PROCESSED_DIR / "geo_zip.parquet"