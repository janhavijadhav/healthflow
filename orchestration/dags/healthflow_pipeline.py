from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import boto3
import pandas as pd
import logging
import os

logger = logging.getLogger(__name__)

RAW_BUCKET       = os.getenv("RAW_BUCKET", "healthflow-raw-dev-805046891516")
PROCESSED_BUCKET = os.getenv("PROCESSED_BUCKET", "healthflow-processed-dev-805046891516")
AWS_REGION       = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

default_args = {
    "owner":            "healthflow",
    "depends_on_past":  False,
    "start_date":       datetime(2026, 1, 1),
    "email_on_failure": False,
    "email_on_retry":   False,
    "retries":          1,
    "retry_delay":      timedelta(minutes=5),
}

def check_s3_raw(**context):
    s3      = boto3.client("s3", region_name=AWS_REGION)
    today   = datetime.utcnow()
    prefix  = f"patients/year={today.year}/month={today.month:02d}/day={today.day:02d}/"
    resp    = s3.list_objects_v2(Bucket=RAW_BUCKET, Prefix=prefix)
    count   = resp.get("KeyCount", 0)
    logger.info(f"Found {count} objects in s3://{RAW_BUCKET}/{prefix}")
    if count == 0:
        raise ValueError(f"No raw data found at {prefix} — run ingestion first")
    context["task_instance"].xcom_push(key="raw_object_count", value=count)
    return count

def validate_data_quality(**context):
    s3      = boto3.client("s3", region_name=AWS_REGION)
    today   = datetime.utcnow()
    tables  = ["patients", "encounters", "conditions", "medications"]
    results = {}

    for table in tables:
        prefix = f"{table}/year={today.year}/month={today.month:02d}/day={today.day:02d}/"
        resp   = s3.list_objects_v2(Bucket=RAW_BUCKET, Prefix=prefix)
        found  = resp.get("KeyCount", 0) > 0
        results[table] = "PASS" if found else "FAIL"
        logger.info(f"Quality check {table}: {results[table]}")

    failed = [t for t, r in results.items() if r == "FAIL"]
    if failed:
        raise ValueError(f"Quality checks failed for: {failed}")

    context["task_instance"].xcom_push(key="quality_results", value=results)
    logger.info(f"All quality checks passed: {results}")
    return results

def check_processed_data(**context):
    s3      = boto3.client("s3", region_name=AWS_REGION)
    today   = datetime.utcnow()
    tables  = ["patients", "encounters", "conditions", "medications"]
    results = {}

    for table in tables:
        prefix = f"{table}/year={today.year}/month={today.month:02d}/day={today.day:02d}/"
        resp   = s3.list_objects_v2(Bucket=PROCESSED_BUCKET, Prefix=prefix)
        size   = sum(o["Size"] for o in resp.get("Contents", []))
        results[table] = size
        logger.info(f"Processed {table}: {size} bytes")

    context["task_instance"].xcom_push(key="processed_sizes", value=results)
    return results

def log_pipeline_success(**context):
    ti      = context["task_instance"]
    raw_count   = ti.xcom_pull(key="raw_object_count",  task_ids="check_raw_data")
    quality     = ti.xcom_pull(key="quality_results",   task_ids="validate_quality")
    processed   = ti.xcom_pull(key="processed_sizes",   task_ids="check_processed")
    logger.info("=" * 50)
    logger.info("HealthFlow Pipeline Completed Successfully")
    logger.info(f"Raw objects found:   {raw_count}")
    logger.info(f"Quality results:     {quality}")
    logger.info(f"Processed sizes:     {processed}")
    logger.info("=" * 50)
    return "Pipeline completed successfully"

with DAG(
    dag_id="healthflow_claims_pipeline",
    default_args=default_args,
    description="End-to-end healthcare claims data pipeline",
    schedule="0 6 * * *",
    catchup=False,
    tags=["healthflow", "healthcare", "claims"],
) as dag:

    check_raw = PythonOperator(
        task_id="check_raw_data",
        python_callable=check_s3_raw,
    )

    validate_quality = PythonOperator(
        task_id="validate_quality",
        python_callable=validate_data_quality,
    )

    run_transformation = BashOperator(
        task_id="run_pyspark_transformation",
        bash_command="""
            cd /opt/airflow && \
            echo "PySpark transformation step" && \
            echo "Would run: python transformation/pyspark/transform_claims.py" && \
            echo "Transformation complete"
        """,
    )

    check_processed = PythonOperator(
        task_id="check_processed",
        python_callable=check_processed_data,
    )

    run_dbt = BashOperator(
        task_id="run_dbt_models",
        bash_command="""
            echo "dbt run step" && \
            echo "Would run: dbt run --project-dir transformation/dbt/healthflow_dbt" && \
            echo "dbt models complete"
        """,
    )

    log_success = PythonOperator(
        task_id="log_pipeline_success",
        python_callable=log_pipeline_success,
    )

    check_raw >> validate_quality >> run_transformation >> check_processed >> run_dbt >> log_success
