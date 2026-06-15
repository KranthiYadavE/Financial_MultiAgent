"""One-shot initializer: generate data → Postgres → Qdrant."""

import time

from generate_sample_data import run_pipeline
from ingest_embeddings import ingest_docs
from load_to_postgres import load_gold_to_postgres
from sqlalchemy import create_engine, text

from shared.config import Settings


def wait_for_postgres(max_retries: int = 30) -> None:
    settings = Settings()
    engine = create_engine(settings.postgres_dsn)
    for i in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("PostgreSQL is ready")
            return
        except Exception:
            print(f"Waiting for PostgreSQL... ({i + 1}/{max_retries})")
            time.sleep(2)
    raise RuntimeError("PostgreSQL not available")


def main() -> None:
    print("=== Step 1: Generate sample data (Medallion pipeline) ===")
    run_pipeline()

    print("=== Step 2: Wait for PostgreSQL ===")
    wait_for_postgres()

    print("=== Step 3: Load Gold layer to PostgreSQL ===")
    load_gold_to_postgres()

    print("=== Step 4: Ingest embeddings to Qdrant ===")
    ingest_docs()

    print("=== Data initialization complete ===")


if __name__ == "__main__":
    main()
