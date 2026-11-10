"""MySQL connection (from .env) and a runner for the analysis .sql files."""
import os
import sys
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from src.config import PROJECT_ROOT, SQL_DIR
from src.exception import CustomException
from src.logger import get_logger


log = get_logger("db")
REQUIRED = ("MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_HOST", "MYSQL_PORT", "MYSQL_DB")


def get_engine():
    """Create a SQLAlchemy engine from the .env file in the project root."""
    load_dotenv(PROJECT_ROOT / ".env")
    missing = [k for k in REQUIRED if not os.getenv(k)]

    if missing:
        raise RuntimeError(f"Missing in .env: {missing}")
    user, host, port, db = (os.getenv(k) for k in ("MYSQL_USER", "MYSQL_HOST", "MYSQL_PORT", "MYSQL_DB"))
    pwd = quote_plus(os.getenv("MYSQL_PASSWORD"))
    log.info("Connection to %s@%s:%s/%s", user, host, port, db)      # password is never logged
    return create_engine(f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}", pool_pre_ping=True)

def read_query(engine, sql, params = None):
    """Run one SELECT and return a DataFrame. Use :name placeholders with params = {'name': value}."""
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)
    except Exception as e:
        raise CustomException(e, sys) from e

    
def run_sql_file(engine, name, timeout_ms = 120000, show = True):
    """Run every statement in sql/<name>; return the result of SELECT as a DataFrame.
    
    Statements are split on ';' so keep ';' out of comments and strings.
    A comment on the first line of a statement is printed as its title.
    """
    path = SQL_DIR / name
    if not path.exists():
        raise CustomException(f"SQL file not found: {path}")
    results = []
    try:
        with engine.begin() as conn:
            if engine.dialect.name == "mysql" and timeout_ms:
                conn.execute(text(f"SET SESSION MAX_EXECUTION_TIME = {int(timeout_ms)}"))
            for stmt in path.read_text(encoding = "utf-8").split(";"):
                lines = stmt.strip().splitlines()
                body = "\n".join(l for l in lines if not l.strip().startswith("--")).strip()
                if not body:
                    continue
                title = lines[0].strip()("- ").strip() if lines and lines[0].startswith("--") else ""
                result = conn.execute(text(body))
                if result.returns_rows:
                    df = pd.DataFrame(result.fetchall(), columns=list(result.keys()))
                    results.append(df)
                    if show:
                        try:
                            from IPython.display import display
                            if title:
                                print(f"\n>>> {title}")
                            display(df)
                        except ImportError:
                            print(df)
        log.info("ran %s: %d result set(s)", name, len(results))
    except CustomException:
        raise
    except Exception as e:
        log.error("failed running %s", name)
        raise CustomException(e) from e
    return results
