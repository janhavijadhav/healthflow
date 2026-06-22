import boto3
import pandas as pd
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RAW_BUCKET   = os.getenv("RAW_BUCKET")
AWS_REGION   = os.getenv("AWS_REGION", "us-east-1")
SAMPLE_DIR   = Path(__file__).parent.parent / "data" / "sample"

TABLES = ["patients", "encounters", "conditions", "medications", "procedures", "observations"]

s3 = boto3.client("s3", region_name=AWS_REGION)

def find_csv(table_name: str) -> Path | None:
    for f in SAMPLE_DIR.rglob("*.csv"):
        if f.stem.lower() == table_name.lower():
            return f
    return None

def upload_table(table_name: str, csv_path: Path) -> dict:
    df = pd.read_csv(csv_path)
    today = datetime.utcnow()
    partition = f"year={today.year}/month={today.month:02d}/day={today.day:02d}"
    s3_key = f"{table_name}/{partition}/{table_name}.csv"

    logger.info(f"Uploading {table_name}: {len(df)} rows → s3://{RAW_BUCKET}/{s3_key}")

    s3.put_object(
        Bucket=RAW_BUCKET,
        Key=s3_key,
        Body=df.to_csv(index=False).encode("utf-8"),
        ContentType="text/csv",
        Metadata={
            "table":      table_name,
            "row_count":  str(len(df)),
            "col_count":  str(len(df.columns)),
            "upload_ts":  datetime.utcnow().isoformat(),
            "source":     "synthea"
        }
    )
    return {"table": table_name, "rows": len(df), "key": s3_key}

def upload_manifest(results: list) -> None:
    manifest = {
        "upload_timestamp": datetime.utcnow().isoformat(),
        "source":           "synthea",
        "project":          "healthflow",
        "tables":           results,
        "total_tables":     len(results),
        "total_rows":       sum(r["rows"] for r in results)
    }
    s3.put_object(
        Bucket=RAW_BUCKET,
        Key=f"_manifests/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_manifest.json",
        Body=json.dumps(manifest, indent=2).encode("utf-8"),
        ContentType="application/json"
    )
    logger.info(f"Manifest uploaded — {manifest['total_rows']} total rows across {manifest['total_tables']} tables")

def main():
    logger.info(f"Starting ingestion → s3://{RAW_BUCKET}")
    results = []
    missing = []

    for table in TABLES:
        csv_path = find_csv(table)
        if not csv_path:
            logger.warning(f"No CSV found for table: {table}")
            missing.append(table)
            continue
        result = upload_table(table, csv_path)
        results.append(result)

    if results:
        upload_manifest(results)

    print("\n── Ingestion Summary ──────────────────")
    for r in results:
        print(f"  ✓ {r['table']:<20} {r['rows']:>6} rows  →  {r['key']}")
    if missing:
        print(f"\n  ⚠ Not found: {', '.join(missing)}")
    print(f"\n  Total: {sum(r['rows'] for r in results)} rows uploaded to S3")

if __name__ == "__main__":
    main()
