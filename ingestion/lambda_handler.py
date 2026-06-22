import json
import logging
import os
import urllib.parse
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Triggered by S3 PutObject on raw bucket claims/ prefix.
    Logs metadata and returns a summary for CloudWatch.
    """
    project     = os.environ.get("PROJECT_NAME", "healthflow")
    environment = os.environ.get("ENVIRONMENT", "dev")
    raw_bucket  = os.environ.get("RAW_BUCKET", "")

    processed_files = []

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key    = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        size   = record["s3"]["object"].get("size", 0)

        logger.info(json.dumps({
            "event":       "s3_object_created",
            "project":     project,
            "environment": environment,
            "bucket":      bucket,
            "key":         key,
            "size_bytes":  size,
            "timestamp":   datetime.utcnow().isoformat()
        }))

        processed_files.append({
            "bucket": bucket,
            "key":    key,
            "size":   size,
            "status": "logged"
        })

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message":         "Ingestion trigger complete",
            "files_processed": len(processed_files),
            "files":           processed_files
        })
    }
