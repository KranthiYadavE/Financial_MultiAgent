"""Load Gold parquet files into PostgreSQL."""

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from shared.config import Settings


def load_gold_to_postgres() -> None:
    settings = Settings()
    engine = create_engine(settings.postgres_dsn)
    data_dir = Path(__file__).resolve().parents[1] / "data" / "gold"

    customers = pd.read_parquet(data_dir / "customers.parquet")
    transactions = pd.read_parquet(data_dir / "transactions.parquet")

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE gold.transactions RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE gold.customers RESTART IDENTITY CASCADE"))

    customers.to_sql("customers", engine, schema="gold", if_exists="append", index=False)
    transactions.to_sql("transactions", engine, schema="gold", if_exists="append", index=False)

    print(f"Loaded {len(customers)} customers and {len(transactions)} transactions to PostgreSQL")


if __name__ == "__main__":
    load_gold_to_postgres()
