"""Pydantic schemas for delivery time prediction."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --------------------------------------------------
# Input schema
# --------------------------------------------------

class OrderIn(BaseModel):

    est_days: float = Field(
        gt=0,
        le=200,
        description="Platform delivery estimate in days",
    )

    customer_zip: int = Field(
        ge=1000,
        le=99999,
        description="Customer ZIP code prefix",
    )

    seller_zip: int = Field(
        ge=1000,
        le=99999,
        description="Seller ZIP code prefix",
    )

    customer_state: Optional[str] = None
    seller_state: Optional[str] = None

    main_category: Optional[str] = None

    n_items: int = Field(default=1, ge=1, le=50)
    n_sellers: int = Field(default=1, ge=1, le=20)

    items_price: Optional[float] = Field(default=None, ge=0)
    freight: Optional[float] = Field(default=None, ge=0)
    weight_g: Optional[float] = Field(default=None, ge=0)

    purchase_datetime: Optional[datetime] = None


# --------------------------------------------------
# Output schema
# --------------------------------------------------

class PredictionOut(BaseModel):

    predicted_days: float
    predicted_delivery_date: str
    platform_estimate_days: float
    platform_minus_model_days: float
    model_trained_on: str
    warnings: list[str]