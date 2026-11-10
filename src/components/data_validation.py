"""Data Validation: Raw-Table structure before cleaning, reconciliation numbers after."""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

from dataclasses import dataclass
from src.components.data_ingestion import load_raw
from src.constants import (EXPECTED, EXPECTED_ROWS, ORDER_STATUSES, REQUIRED_COLUMNS,
                           REVENUE_TOLERANCE, UNIQUE_KEYS)
from src.exception import CustomException
from src.logger import get_logger

log = get_logger("validation")

@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""

def run_checks(checks, strict=True):
    """Log every check, return a report DataFrame; raise if strict and any check failed."""
    for c in checks:
        (log.info if c.passed else log.error)("%s - %s %s", "PASS" if c.passed else "FAIL", c.name, c.detail)
    report = pd.DataFrame([c.__dict__ for c in checks])
    failed = [c.name for c in checks if not c.passed]
    if strict and failed:
        raise CustomException(f"{len(failed)} validation checks(s) failed: {failed}")
    return report

def validate_raw(data, check_row_counts = True, strict = True):
    """data: dict of raw DataFrame keyed like config.RAW_FILES."""
    checks = []
    for table, cols in REQUIRED_COLUMNS.items():
        if table not in data:
            checks.append(Check(f"{table}: table present", False))
            continue
        df = data[table]
        missing = [c for c in cols if c not in df.columns]
        checks.append(Check(f"{table}: required columns", not missing, f"missing {missing}" if missing else ""))
        if missing:
            continue
        if check_row_counts:
            checks.append(Check(f"{table}: row count", len(df) == EXPECTED_ROWS[table],
                                f"{len(df):,} (expected {EXPECTED_ROWS[table]:,})"))
        if table in UNIQUE_KEYS:
            dup = int(df.duplicated(subset = UNIQUE_KEYS[table]).sum())
            checks.append(Check(f"{table}: key {UNIQUE_KEYS[table]} unique", dup == 0, f"{dup} duplicates"))

    if "order_items" in data and {"price", "freight_value"} <= set(data["order_items"].columns):
        it = data["order_items"]
        checks.append(Check("order_items: price > 0 and freight >= 0",
                            bool((it["price"] > 0).all() and (it["freight_value"] >= 0).all())))
    if "payments" in data and "payment_value" in data["payments"].columns:
        checks.append(Check("payments: payment_value >= 0", bool((data["payments"]["payment_value"] >= 0).all())))
    if "orders" in data and "order_status" in data["orders"].columns:
        unknown = set(data["orders"]["order_status"].dropna().unique()) - ORDER_STATUSES
        checks.append(Check("orders: known order_status values", not unknown, f"unknown {sorted(unknown)}" if unknown else ""))
    if {"orders", "customers"} <= set(data):
        orphans = (~data["orders"]["customer_id"].isin(data["customers"]["customer_id"])).sum()
        checks.append(Check("orders -> customers: no orphan customer_id", orphans == 0, f"{orphans} orphans"))
    if {"order_items", "orders"} <= set(data):
        orphans = (~data["order_items"]["order_id"].isin(data["orders"]["order_id"])).sum()
        checks.append(Check("order_items -> orders: no orphan order_id", orphans == 0, f"{orphans} orphans"))
    return run_checks(checks, strict)


def validate_clean(orders_clean, strict = True):
    """Reconcile the cleaned order table with the numbers fixed in notebook 4 to 12."""
    need = {"order_id", "customer_unique_id", "revenue", "is_valid_sale", "in_delivery_analysis"}
    absent = need - set(orders_clean.columns)
    if absent:
        raise CustomException(f"order_clean is missing columns: {sorted(absent)}")
    valid = orders_clean[orders_clean["is_valid_sale"]]
    per_customer = valid.groupby("customer_unique_id").size()
    revenue = float(valid["revenue"].sum())
    n_deliv = int((orders_clean["is_valid_sale"] & orders_clean['in_delivery_analysis']).sum())
    checks = [
        Check("order_id unique", bool(orders_clean["order_id"].is_unique)),
        Check("valid orders", len(valid) == EXPECTED["valid_orders"], f"{len(valid):,} (expected {EXPECTED['valid_orders']:,})"),
        Check("unique customers", len(per_customer) == EXPECTED["customers"], f"{len(per_customer):,} (expected {EXPECTED['customers']:,})"),
        Check("revenue", abs(revenue - EXPECTED["revenue"]) < REVENUE_TOLERANCE, f"{revenue:,.2f} (expected {EXPECTED['revenue']:,.2f})"),
        Check("repeat customers", int((per_customer > 1).sum()) == EXPECTED["repeat_customers"], f"{int((per_customer > 1).sum()):,} (expected {EXPECTED['repeat_customers']:,})"),
        Check("delivered valiid orders", n_deliv == EXPECTED["delivered_valid_orders"], f"{n_deliv:,} (expected {EXPECTED['delivered_valid_orders']:,})"),
    ]
    return run_checks(checks, strict)


def _same_missing(df):
    """Parquet stores missing values in object columns as None, memory uses NaN; treat them as equal."""
    df = df.reset_index(drop = True).copy()
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].where(df[c].notna(), np.nan)
    return df


def compare_with_saved(outputs, saved_dir, strict = False):
    """Parity check: every dataset must equal the parquet file saved earlier (same columns, order, values)."""
    checks = []
    for name, df in outputs.items():
        path = Path(saved_dir) / f"{name}.parquet"
        if not path.exists():
            checks.append(Check(f"{name}: saved file exists", False, str(path)))
            continue
        old = pd.read_parquet(path)
        if list(old.columns) != list(df.columns):
            diff = sorted(set(old.columns) ^ set(df.columns)) or "same columns, different order"
            checks.append(Check(f"{name}: columns", False, f"{diff}"))
            continue
        if old.shape != df.shape:
            checks.append(Check(f"{name}: shape", False, f"{df.shape} vs saved {old.shape}"))
            continue
        try:
            pd.testing.assert_frame_equal(_same_missing(df), _same_missing(old),
                                          check_dtype=True, check_exact=False, rtol=1e-9)
            checks.append(Check(f"{name}: identical to saved file", True, str(df.shape)))
        except AssertionError as e:
            checks.append(Check(f"{name}: identical to saved file", False, str(e).splitlines()[0][:150]))
    return run_checks(checks, strict)


if __name__ == "__main__":
    data = load_raw()
    for name, df in data.items():
        log.info("shape %-12s %s", name, df.shape)
    report = validate_raw(data, strict=False)
    print(report.to_string(index=False))
    n_failed = int((~report["passed"]).sum())
    log.info("%d of %d checks passed", len(report) - n_failed, len(report))
    sys.exit(1 if n_failed else 0)