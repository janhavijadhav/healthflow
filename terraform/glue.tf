resource "aws_glue_catalog_database" "healthflow" {
  name        = "${var.project_name}_${var.environment}"
  description = "HealthFlow data catalog database"
}

resource "aws_glue_crawler" "raw_crawler" {
  database_name = aws_glue_catalog_database.healthflow.name
  name          = "${var.project_name}-raw-crawler-${var.environment}"
  role          = aws_iam_role.glue_role.arn
  schedule      = "cron(0 6 * * ? *)"

  s3_target {
    path = "s3://${aws_s3_bucket.raw.bucket}/claims/"
  }

  s3_target {
    path = "s3://${aws_s3_bucket.raw.bucket}/patients/"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = { AddOrUpdateBehavior = "InheritFromTable" }
    }
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_glue_crawler" "processed_crawler" {
  database_name = aws_glue_catalog_database.healthflow.name
  name          = "${var.project_name}-processed-crawler-${var.environment}"
  role          = aws_iam_role.glue_role.arn

  s3_target {
    path = "s3://${aws_s3_bucket.processed.bucket}/claims/"
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}
