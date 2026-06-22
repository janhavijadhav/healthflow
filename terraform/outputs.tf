output "raw_bucket_name" {
  description = "S3 raw zone bucket name"
  value       = aws_s3_bucket.raw.bucket
}

output "processed_bucket_name" {
  description = "S3 processed zone bucket name"
  value       = aws_s3_bucket.processed.bucket
}

output "curated_bucket_name" {
  description = "S3 curated zone bucket name"
  value       = aws_s3_bucket.curated.bucket
}

output "lambda_function_name" {
  description = "Lambda ingestion trigger function name"
  value       = aws_lambda_function.ingestion_trigger.function_name
}

output "glue_database_name" {
  description = "Glue catalog database name"
  value       = aws_glue_catalog_database.healthflow.name
}

output "lambda_role_arn" {
  description = "IAM role ARN for Lambda"
  value       = aws_iam_role.lambda_role.arn
}
