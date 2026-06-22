import boto3
import os
import logging
import pandas as pd
from datetime import datetime, UTC
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from dotenv import load_dotenv
import tempfile

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_BUCKET = os.getenv("PROCESSED_BUCKET")
AWS_REGION       = os.getenv("AWS_REGION", "us-east-1")
SAMPLE_DIR       = Path(__file__).parent.parent.parent / "data" / "sample"

today     = datetime.now(UTC)
PARTITION = f"year={today.year}/month={today.month:02d}/day={today.day:02d}"

s3 = boto3.client("s3", region_name=AWS_REGION)


def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("healthflow-transform")
        .master("local[*]")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.sql.execution.arrow.pyspark.enabled", "false")
        .getOrCreate()
    )


def find_csv(table: str) -> Path | None:
    for f in SAMPLE_DIR.rglob("*.csv"):
        if f.stem.lower() == table.lower():
            return f
    return None


def transform_patients(spark, csv_path: Path):
    df = spark.read.option("header", "true").option("inferSchema", "true").csv(str(csv_path))
    return (
        df
        .withColumnRenamed("Id",        "patient_id")
        .withColumnRenamed("BIRTHDATE", "birth_date")
        .withColumnRenamed("DEATHDATE", "death_date")
        .withColumnRenamed("GENDER",    "gender")
        .withColumnRenamed("RACE",      "race")
        .withColumnRenamed("ETHNICITY", "ethnicity")
        .withColumnRenamed("STATE",     "state")
        .withColumnRenamed("ZIP",       "zip_code")
        .withColumn("birth_date",  F.to_date("birth_date"))
        .withColumn("death_date",  F.to_date("death_date"))
        .withColumn("age_years",
            F.floor(F.datediff(F.current_date(), F.col("birth_date")) / 365))
        .withColumn("is_deceased", F.col("death_date").isNotNull().cast("boolean"))
        .withColumn("processed_at", F.current_timestamp())
        .select("patient_id", "birth_date", "death_date", "gender",
                "race", "ethnicity", "state", "zip_code",
                "age_years", "is_deceased", "processed_at")
        .dropDuplicates(["patient_id"])
        .filter(F.col("patient_id").isNotNull())
    )


def transform_encounters(spark, csv_path: Path):
    df = spark.read.option("header", "true").option("inferSchema", "true").csv(str(csv_path))
    return (
        df
        .withColumnRenamed("Id",                 "encounter_id")
        .withColumnRenamed("PATIENT",            "patient_id")
        .withColumnRenamed("PROVIDER",           "provider_id")
        .withColumnRenamed("PAYER",              "payer_id")
        .withColumnRenamed("ENCOUNTERCLASS",     "encounter_class")
        .withColumnRenamed("CODE",               "encounter_code")
        .withColumnRenamed("DESCRIPTION",        "description")
        .withColumnRenamed("BASE_ENCOUNTER_COST","base_cost")
        .withColumnRenamed("TOTAL_CLAIM_COST",   "total_claim_cost")
        .withColumnRenamed("PAYER_COVERAGE",     "payer_coverage")
        .withColumnRenamed("START",              "encounter_start")
        .withColumnRenamed("STOP",               "encounter_stop")
        .withColumn("encounter_start",  F.to_timestamp("encounter_start"))
        .withColumn("encounter_stop",   F.to_timestamp("encounter_stop"))
        .withColumn("duration_hours",
            F.round(
                (F.unix_timestamp("encounter_stop") - F.unix_timestamp("encounter_start")) / 3600,
            2))
        .withColumn("out_of_pocket",
            F.round(F.col("total_claim_cost") - F.col("payer_coverage"), 2))
        .withColumn("encounter_date",  F.to_date("encounter_start"))
        .withColumn("encounter_year",  F.year("encounter_start"))
        .withColumn("encounter_month", F.month("encounter_start"))
        .withColumn("processed_at",    F.current_timestamp())
        .select("encounter_id", "patient_id", "provider_id", "payer_id",
                "encounter_class", "encounter_code", "description",
                "encounter_start", "encounter_stop", "encounter_date",
                "encounter_year", "encounter_month", "duration_hours",
                "base_cost", "total_claim_cost", "payer_coverage",
                "out_of_pocket", "processed_at")
        .dropDuplicates(["encounter_id"])
        .filter(F.col("encounter_id").isNotNull())
    )


def transform_conditions(spark, csv_path: Path):
    df = spark.read.option("header", "true").option("inferSchema", "true").csv(str(csv_path))
    return (
        df
        .withColumnRenamed("PATIENT",     "patient_id")
        .withColumnRenamed("ENCOUNTER",   "encounter_id")
        .withColumnRenamed("CODE",        "condition_code")
        .withColumnRenamed("DESCRIPTION", "condition_description")
        .withColumnRenamed("START",       "onset_date")
        .withColumnRenamed("STOP",        "resolution_date")
        .withColumn("onset_date",      F.to_date("onset_date"))
        .withColumn("resolution_date", F.to_date("resolution_date"))
        .withColumn("is_chronic",
            F.col("resolution_date").isNull().cast("boolean"))
        .withColumn("days_active",
            F.when(F.col("resolution_date").isNotNull(),
                F.datediff(F.col("resolution_date"), F.col("onset_date")))
            .otherwise(F.datediff(F.current_date(), F.col("onset_date"))))
        .withColumn("processed_at", F.current_timestamp())
        .select("patient_id", "encounter_id", "condition_code",
                "condition_description", "onset_date", "resolution_date",
                "is_chronic", "days_active", "processed_at")
        .filter(F.col("patient_id").isNotNull())
    )


def transform_medications(spark, csv_path: Path):
    df = spark.read.option("header", "true").option("inferSchema", "true").csv(str(csv_path))
    return (
        df
        .withColumnRenamed("PATIENT",        "patient_id")
        .withColumnRenamed("ENCOUNTER",      "encounter_id")
        .withColumnRenamed("CODE",           "medication_code")
        .withColumnRenamed("DESCRIPTION",    "medication_description")
        .withColumnRenamed("BASE_COST",      "base_cost")
        .withColumnRenamed("PAYER_COVERAGE", "payer_coverage")
        .withColumnRenamed("TOTALCOST",      "total_cost")
        .withColumnRenamed("START",          "start_date")
        .withColumnRenamed("STOP",           "stop_date")
        .withColumn("start_date",    F.to_date("start_date"))
        .withColumn("stop_date",     F.to_date("stop_date"))
        .withColumn("is_active",     F.col("stop_date").isNull().cast("boolean"))
        .withColumn("out_of_pocket",
            F.round(F.col("total_cost") - F.col("payer_coverage"), 2))
        .withColumn("processed_at", F.current_timestamp())
        .select("patient_id", "encounter_id", "medication_code",
                "medication_description", "start_date", "stop_date",
                "is_active", "base_cost", "payer_coverage",
                "total_cost", "out_of_pocket", "processed_at")
        .filter(F.col("patient_id").isNotNull())
    )


def write_parquet_to_s3(df, table: str) -> int:
    count = df.count()
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, table)
        df.coalesce(1).write.mode("overwrite").option("compression", "snappy").parquet(local_path)

        for fname in os.listdir(local_path):
            if fname.endswith(".parquet"):
                local_file = os.path.join(local_path, fname)
                s3_key     = f"{table}/{PARTITION}/{table}.parquet"
                s3.upload_file(local_file, PROCESSED_BUCKET, s3_key)
                logger.info(f"Uploaded → s3://{PROCESSED_BUCKET}/{s3_key}")
                break

    return count


def main():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    transforms = {
        "patients":    transform_patients,
        "encounters":  transform_encounters,
        "conditions":  transform_conditions,
        "medications": transform_medications,
    }

    print("\n── PySpark Transformation Summary ─────")
    for table, transform_fn in transforms.items():
        csv_path = find_csv(table)
        if not csv_path:
            print(f"  ⚠ SKIP  {table:<20} — CSV not found")
            continue
        transformed = transform_fn(spark, csv_path)
        count       = write_parquet_to_s3(transformed, table)
        print(f"  ✓ {table:<20} {count:>6} rows → s3://{PROCESSED_BUCKET}/{table}/{PARTITION}/")

    spark.stop()
    print("\n  Transformation complete")


if __name__ == "__main__":
    main()
