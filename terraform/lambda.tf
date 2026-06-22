data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../ingestion/lambda_handler.py"
  output_path = "${path.module}/lambda_function.zip"
}

resource "aws_lambda_function" "ingestion_trigger" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-ingestion-trigger-${var.environment}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_handler.handler"
  runtime          = "python3.12"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 60
  memory_size      = 128

  environment {
    variables = {
      PROJECT_NAME      = var.project_name
      ENVIRONMENT       = var.environment
      RAW_BUCKET        = aws_s3_bucket.raw.bucket
      PROCESSED_BUCKET  = aws_s3_bucket.processed.bucket
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestion_trigger.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.raw.arn
}

resource "aws_s3_bucket_notification" "raw_trigger" {
  bucket = aws_s3_bucket.raw.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.ingestion_trigger.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "claims/"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}
