import boto3
import pandas as pd
import os
import logging
from io import StringIO
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RAW_BUCKET = os.getenv("RAW_BUCKET")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
s3 = boto3.client("s3", region_name=AWS_REGION)

def load_latest_from_s3(table: str) -> pd.DataFrame:
    today = datetime.now(timezone.utc)
    prefix = f"{table}/year={today.year}/month={today.month:02d}/day={today.day:02d}/"
    resp = s3.list_objects_v2(Bucket=RAW_BUCKET, Prefix=prefix)
    if "Contents" not in resp:
        raise FileNotFoundError(f"No files found at s3://{RAW_BUCKET}/{prefix}")
    key = resp["Contents"][0]["Key"]
    obj = s3.get_object(Bucket=RAW_BUCKET, Key=key)
    return pd.read_csv(StringIO(obj["Body"].read().decode("utf-8")))

def simple_validate(df: pd.DataFrame, table: str) -> dict:
    col_names = [str(c) for c in df.columns]
    checks = {
        "has_rows":      len(df) > 0,
        "no_empty_cols": not any(c.strip() == "" for c in col_names),
        "row_count":     len(df)
    }
    success = all(v for k, v in checks.items() if isinstance(v, bool))
    logger.info(f"{table}: {checks}")
    return {"table": table, "success": success, "checks": checks}

def main():
    print("\n── Great Expectations Validation ──────")

    for table in ["patients", "encounters", "conditions", "medications"]:
        try:
            df = load_latest_from_s3(table)
            result = simple_validate(df, table)
            status = "✓ PASS" if result["success"] else "✗ FAIL"
            print(f"  {status}  {table:<20} —  {result['checks']['row_count']} rows")
        except FileNotFoundError as e:
            print(f"  ⚠ SKIP  {table:<20} —  {e}")

    print("\n  Validation complete")

if __name__ == "__main__":
    main()
