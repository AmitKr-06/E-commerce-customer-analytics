"""FastAPI application for the Delivery Time Estimator."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.schemas import OrderIn, PredictionOut
from src.logger import get_logger
from src.model.model_prediction import Predictor


# --------------------------------------------------
# Application configuration
# --------------------------------------------------

log = get_logger("api")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


# --------------------------------------------------
# Verify required directories
# --------------------------------------------------

if not TEMPLATE_DIR.exists():
    raise RuntimeError(f"Templates directory not found: {TEMPLATE_DIR}")

if not STATIC_DIR.exists():
    raise RuntimeError(f"Static directory not found: {STATIC_DIR}")


# --------------------------------------------------
# Configure Jinja2 templates
# --------------------------------------------------

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


# --------------------------------------------------
# Load ML model during application startup
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Loading delivery prediction model...")
    app.state.predictor = Predictor()
    log.info("Prediction model loaded successfully.")
    yield
    log.info("Application shutting down.")


# --------------------------------------------------
# Initialize FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="Delivery Time Estimator",
    description="Machine learning powered e-commerce delivery time prediction.",
    version="1.0.0",
    lifespan=lifespan,
)


# --------------------------------------------------
# Register static files  ← MUST come before any
# route that calls url_for('static', ...)
# --------------------------------------------------

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)


# --------------------------------------------------
# Homepage
# --------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    predictor = request.app.state.predictor

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "states": sorted(predictor.categories["customer_state"]),
            "categories": sorted(predictor.categories["main_category"]),
            "trained_on": predictor.trained_on,
        },
    )


# --------------------------------------------------
# Delivery time prediction endpoint
# --------------------------------------------------

@app.post("/predict", response_model=PredictionOut)
def predict(order: OrderIn, request: Request):
    try:
        predictor = request.app.state.predictor
        input_data = order.model_dump()
        return predictor.predict(input_data)

    except Exception as e:
        log.exception("Prediction failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Prediction failed. Please check the input values.",
        )


# --------------------------------------------------
# Health check endpoint
# --------------------------------------------------

@app.get("/health")
def health(request: Request):
    predictor = request.app.state.predictor
    return {
        "status": "ok",
        "model_trained_on": predictor.trained_on,
    }
