import os
import boto3
import pandas as pd
import pandas_gbq
import tempfile
import logging
from pathlib import Path
from datetime import datetime, UTC
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_BUCKET = os.getenv("PROCESSED_BUCKET")
GCP_PROJECT      = "healthflow-analytics-500100"
BQ_DATASET       = "healthflow_dev"
AWS_REGION       = os.getenv("AWS_REGION", "us-east-1")

s3     = boto3.client("s3", region_name=AWS_REGION)
today  = datetime.now(UTC)
PARTITION = f"year={today.year}/month={today.month:02d}/day={today.day:02d}"

TABLES = ["patients", "encounters", "conditions", "medications"]

def download_parquet(table: str) -> pd.DataFrame:
    key = f"{table}/{PARTITION}/{table}.parquet"
    logger.info(f"Downloading s3://{PROCESSED_BUCKET}/{key}")
    with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
        s3.download_file(PROCESSED_BUCKET, key, tmp.name)
        return pd.read_parquet(tmp.name)

def load_to_bigquery(df: pd.DataFrame, table: str) -> None:
    destination = f"{BQ_DATASET}.{table}"
    logger.info(f"Loading {len(df)} rows → BigQuery {destination}")
    pandas_gbq.to_gbq(
        df,
        destination,
        project_id=GCP_PROJECT,
        if_exists="replace",
        progress_bar=False
    )

def main():
    print("\n── BigQuery Load Summary ───────────────")
    for table in TABLES:
        df    = download_parquet(table)
        load_to_bigquery(df, table)
        print(f"  ✓ {table:<20} {len(df):>6} rows → BigQuery {BQ_DATASET}.{table}")
    print("\n  Load complete")

if __name__ == "__main__":
    main()
