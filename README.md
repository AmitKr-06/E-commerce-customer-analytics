# E-commerce Customer Analytics

End-to-end analysis of the Olist Brazilian e-commerce marketplace (Oct 2016 to Aug 2018): data cleaning and validation, statistical tests, customer segmentation (RFM and K-Means), delivery and review analysis, a delivery-time prediction model with MLflow tracking and a model registry, and a FastAPI web app that serves the model.

> **Main finding:** late delivery is the biggest identified driver of bad reviews, and customer retention is the biggest revenue gap. Only 3.04% of customers ordered twice.

![App screenshot](docs/app_screenshot.png)

---

## Contents

- [Business questions](#business-questions)
- [Key findings](#key-findings)
- [Delivery-time model](#delivery-time-model)
- [Project structure](#project-structure)
- [Setup](#setup)
- [Running the pipeline](#running-the-pipeline)
- [Model tracking and registry](#model-tracking-and-registry)
- [Web app and API](#web-app-and-api)
- [Tests](#tests)
- [Data quality rules](#data-quality-rules)
- [Limitations](#limitations)
- [Roadmap](#roadmap)

---

## Business questions

1. Who are the valuable customers, and how many of them come back?
2. Where is delivery time lost, and how much does lateness hurt reviews?
3. Can delivery time be predicted at purchase time better than the platform's own estimate?
4. What should the business do first?

## Key findings

All numbers reconcile across the notebooks, the SQL layer and the Python pipeline (checked in code).

**Dataset:** 98,198 valid orders, 94,982 customers, R$15,738,221.95 revenue. 96.96% of customers bought only once.

### Late delivery and reviews

| Metric | On time | Late |
|---|---|---|
| Average review score | 4.29 | 2.57 |
| Bad reviews (score 1 to 2) | 9.22% | 54.06% |

- 8.11% of delivered orders were late.
- Late orders are 8.0% of reviewed orders but 33.7% of all bad reviews. At most about 28% of bad reviews can be linked to lateness (upper bound). 66.3% come from on-time orders.
- Reviews fall sharply once an order is more than 2 days late: average 3.92 at 0 to 2 days late, 2.81 at 2 to 5 days, 1.89 at 5 to 10 days.
- The odds of a bad review are about 12 times higher for late orders (odds ratio 11.93, 95% CI 11.33 to 12.57), and controls for state, category, price, freight, weight and items do not weaken it.
- Late orders take 31.53 days against 10.93 for on-time orders. 86% of the extra time is in the carrier-to-customer stage.
- The late rate differs by state (chi-square, Cramer's V 0.13, small effect): SP 5.89% against 9.72% elsewhere.
- The top 10% of sellers by late orders produce 72.7% of late orders but also handle 63.3% of all orders, so lateness is concentrated mostly because of volume.

### Customer segments (rule-based RFM)

| Segment | Customers | Customer share | Revenue share | Avg spend |
|---|---|---|---|---|
| Lapsed high spenders | 21,050 | 22.16% | 40.07% | R$299.58 |
| Recent high spenders | 14,648 | 15.42% | 28.20% | R$303.01 |
| Lapsed low spenders | 34,291 | 36.10% | 15.81% | R$72.55 |
| Recent customers | 22,106 | 23.27% | 10.26% | R$73.08 |
| Repeat but lapsing | 1,648 | 1.74% | 3.13% | R$298.54 |
| Champions | 1,239 | 1.30% | 2.53% | R$321.54 |

- Spending matters more than recency: the two one-time high-spender groups are 37.6% of customers and bring 68.3% of revenue.
- Repeat buyers spend about the same as one-time high spenders, so the value is in getting a second order.
- Segments are my own rules (R and M in quintiles, F in fixed bands), not a standard.

### K-Means clustering

K-Means (k = 4) on recency and log(1 + total spend). Frequency is not a feature, because 97% of customers have one order and the repeat buyers would dominate the clustering. Silhouette is about 0.35 and adjusted Rand index across seeds is 0.907 to 0.998.

| Cluster | Customers | Revenue share | Avg spend |
|---|---|---|---|
| High spenders | 12.84% | 41.96% | R$541.30 |
| Recent mid spenders | 32.46% | 31.62% | R$161.41 |
| Long-lapsed mid-to-low spenders | 27.44% | 17.59% | R$106.25 |
| Low spenders | 27.26% | 8.83% | R$53.66 |

The clusters split a continuous range of customers and are not natural groups. Agreement with the RFM rules is partial (ARI 0.249).

## Delivery-time model

**Task:** at purchase time, predict how many days delivery will take.

- **Data:** 96,469 delivered valid orders, one row per order.
- **Features (all known at purchase):** platform estimate, customer-seller distance (haversine on zip-prefix medians), customer and seller state, main category, items, sellers, price, freight, weight, volume, purchase month, weekday and hour. A leakage check blocks any feature known only after delivery.
- **Model:** `HistGradientBoostingRegressor`, absolute-error loss, fitted on train + valid.
- **Split by time:** train before 2018-03-01 (57,316), validation March to April 2018 (13,801), test May to August 2018 (25,352).

**Test-period results (days):**

| Model | MAE | Median abs. error | Bias |
|---|---|---|---|
| Platform estimate | 12.67 | 11.33 | +11.98 |
| Median of train + valid | 5.29 | 4.75 | +1.94 |
| Line on estimated days | 5.21 | 4.28 | +2.82 |
| **Gradient boosting** | **3.72** | **2.71** | **+0.36** |

**Be careful with these results:**
- Across three earlier rolling validation periods the model was only 4% better than a straight line (MAE 6.23 against 6.49), and worse in Jan to Feb 2018. The test gain (29%) is larger than in earlier periods, and the reason was not tested.
- The **late-or-not classifier is not reliable** (AUROC 0.728 against 0.715 for the estimated days alone; average precision lower). It is kept as a diagnostic only.
- **Model-based date ranges (P90) are not ready for use**: coverage was 74% to 83% in earlier periods against a 90% target.
- Rounds that did not meet their pre-set adoption rules (seller and route history, shipping-deadline features, dropping purchase month) were not adopted.

Use the regression for an expected delivery time, not for date promises or late alerts.

## Project structure

```
E-commerce-customer-analytics/
├── app/                          # FastAPI web app
│   ├── main.py                   # routes: /, /predict, /health
│   ├── schemas.py                # request and response models
│   ├── templates/index.html
│   └── static/style.css
├── data/
│   ├── raw/                      # Olist CSV files (not in git)
│   ├── interim/
│   └── processed/                # cleaned parquet files, model_dataset, geo_zip
├── models/                       # saved models (not in git)
├── notebooks/                    # analysis notebooks (see below)
├── reports/                      # metrics.json, experiment_info.json, figures
├── sql/                          # MySQL analysis queries
├── src/
│   ├── components/
│   │   ├── data_ingestion.py     # read raw CSVs
│   │   ├── data_validation.py    # structure and reconciliation checks
│   │   ├── data_transformation.py# cleaning and order/item tables
│   │   └── feature_engineering.py# model dataset, RFM scoring
│   ├── model/
│   │   ├── model_building.py     # rolling CV, train regressor and classifier
│   │   ├── model_evaluation.py   # test metrics, checks, MLflow logging
│   │   ├── model_registry.py     # register, alias staging, promote to production
│   │   └── model_prediction.py   # Predictor class (used by the API)
│   ├── config.py                 # paths
│   ├── constants.py              # business rules, features, model settings
│   ├── db.py                     # MySQL connection and SQL runner
│   ├── exception.py              # CustomException with file and line
│   ├── logger.py                 # console and rotating file logger
│   ├── mlflow_utils.py           # local or DagsHub tracking setup
│   └── utils.py
├── tests/                        # pytest suite
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

### Notebooks

| Notebook | Content |
|---|---|
| 01 to 06 | Data loading, SQL layer, cleaning and descriptive analysis (fill in) |
| 07 | Statistical analysis: Mann-Whitney, Kruskal-Wallis, chi-square, effect sizes |
| 08 | RFM analysis and rule-based segments |
| 09 | K-Means customer segmentation |
| 10 | Delivery stages and review analysis, logistic regression |
| 11 | Delivery-time prediction model, baselines, rolling validation, SHAP |
| 12 | Business recommendations and scenarios |

The notebooks read from MySQL (`valid_orders_t`, `latest_review_t`). The `src/` pipeline reads the raw CSVs. Both reproduce the same reference numbers.

## Setup

**Requirements:** Python 3.11, MySQL (only for the notebooks).

```bash
git clone https://github.com/AmitKr-06/E-commerce-customer-analytics.git
cd E-commerce-customer-analytics

conda create -n ecommerce python=3.11
conda activate ecommerce
pip install -r requirements.txt
```

**Data:** download the Olist Brazilian E-Commerce dataset from Kaggle and place the CSV files in `data/raw/` with these names: `customers.csv`, `geolocation.csv`, `order_items.csv`, `order_payments.csv`, `order_review.csv`, `orders.csv`, `products.csv`, `sellers.csv`, `product_category_name.csv`. Check the dataset's license on Kaggle before reusing it.

**Environment variables:** create a `.env` file in the project root (it is in `.gitignore`; never commit it).

```env
# MySQL (notebooks and src/db.py)
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_HOST=
MYSQL_PORT=
MYSQL_DB=olist_ecommerce

# DagsHub MLflow (optional; without a token, MLflow runs locally with sqlite)
DAGSHUB_TOKEN=
DAGSHUB_REPO_OWNER=
DAGSHUB_REPO_NAME=
```

The token is in DagsHub under *Settings → Tokens*.

## Running the pipeline

Run from the project root, in this order:

```bash
# 1. Ingest, validate, transform and save the cleaned tables
python -m src.components.data_transformation
# (writes data/processed/*.parquet via save_processed)

# 2. Build the model dataset, run rolling CV, train and save the models
python -m src.model.model_building

# 3. Evaluate on the test period, check against the reference numbers, log to MLflow
python -m src.model.model_evaluation

# 4. Register the model (alias: staging)
python -m src.model.model_registry

# 5. Promote staging to production
python -m src.model.model_registry --promote
```

**Built-in checks:** every stage compares its output with the numbers fixed in the notebooks (orders, customers, revenue, repeat customers, split sizes, late rate, segment sizes, test metrics). A failed check stops the run, or marks the evaluation as not passed, in which case the registry refuses to register the model.

**Try a prediction from the command line:**
```bash
python -m src.model.model_prediction
```

## Model tracking and registry

- **Tracking:** parameters, metrics (test and CV), the model and the model bundle are logged to MLflow. The bundle holds the model, feature list and category levels, so new data is encoded the same way as in training.
- **Backend:** DagsHub when `DAGSHUB_TOKEN` is set, otherwise a local `mlflow.db` (sqlite).
- **Registry:** model name `delivery_time_regressor`. `staging` is set on registration, and `production` is a separate, deliberate step (`--promote`). The promote step refuses versions whose evaluation checks did not pass. To roll back, point `production` at an older version:
  ```bash
  python -m src.model.model_registry --promote --version 1
  ```

Local MLflow UI (when not using DagsHub):
```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

## Web app and API

```bash
uvicorn app.main:app --reload
```

- **Page:** `http://127.0.0.1:8000`. A form for one order that shows the predicted days, expected delivery date, platform estimate and difference.
- **API docs:** `http://127.0.0.1:8000/docs`
- **Health:** `GET /health`

**Example request**
```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"est_days": 20, "customer_zip": 1037, "seller_zip": 1046,
       "customer_state": "SP", "seller_state": "SP",
       "main_category": "beleza_saude", "items_price": 80, "freight": 15,
       "weight_g": 500, "purchase_datetime": "2018-06-10T14:30:00"}'
```

**Response**
```json
{
  "predicted_days": 7.5,
  "predicted_delivery_date": "2018-06-18",
  "platform_estimate_days": 20.0,
  "platform_minus_model_days": 12.5,
  "model_trained_on": "orders up to 2018-04-30",
  "warnings": []
}
```

Only `est_days`, `customer_zip` and `seller_zip` are required. Missing optional values are handled by the model, and unknown zip prefixes or categories return a warning instead of an error.

## Tests

```bash
pip install -r requirements-dev.txt
pytest                                   # all tests
pytest --cov=src --cov-report=term-missing
```

The suite covers cleaning rules, payments aggregation, distance, RFM scoring rules, validation checks, the evaluation checks, the saved model, the predictor and the API. Tests that need the trained model or `geo_zip.parquet` skip themselves when those files are not present. The tests use small synthetic data, so they need neither the raw CSVs nor MySQL.

## Data quality rules

- **Valid sale:** not canceled or unavailable, has a payment, has items.
- **Delivery analysis:** delivered orders with a delivery date. Late means delivered after the estimated date.
- **Flags, not removals:** extreme delivery times (over 60 days) and timestamp inconsistencies (for example, carrier handover before approval) are flagged and kept. Stage-time results exclude 1,388 orders with missing or negative stage times.
- **Geolocation:** 42 coordinate rows outside Brazil were dropped, and the median coordinate per zip prefix is used. 477 orders have no distance and stay as missing values.
- **Categories:** two product categories with no English name were translated by hand. Orders with no category are labeled `unknown`.
- **Trend window:** months outside Jan 2017 to Aug 2018 are incomplete and excluded from trend charts.

All rules live in `src/constants.py`.

## Limitations

- The data is observational, so results show associations, not causes.
- Only delivered orders are in the delivery data. Slow orders still undelivered at the end of the data are missing, which probably makes recent months look faster.
- Review results use only reviewed orders, and customers with a bad experience may be more likely to review.
- There is no cost, margin, marketing or carrier data, so the business scenarios show size, not profit.
- The three periods differ a lot in speed and late rate (7.7% in train, 13.5% in validation, 6.2% in test), so model results depend on the period.
- Purchase-time data cannot see carrier problems, strikes or weather.
- The test period was used to report several final models, so it is not a fresh hold-out for each one.
- Feature importance and SHAP values are descriptive, not causal.

## Roadmap

- Containerize the app with Docker
- CI/CD pipeline (tests, image build, deployment)
- Re-evaluate the model on newer data before relying on it, since its advantage varied by period

## Author

**Amit Kumar** ([@AmitKr-06](https://github.com/AmitKr-06))

Dataset: [Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) on Kaggle.