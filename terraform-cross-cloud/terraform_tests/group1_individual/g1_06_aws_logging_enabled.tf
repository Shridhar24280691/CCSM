terraform {
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
}

provider "aws" {
  region = "eu-west-1"
}

# TEST: AWS bucket with logging enabled
# EXPECTED: No logging finding (should pass)

resource "aws_s3_bucket" "g1_06" {
  bucket = "g1-06-logging-on"
}

resource "aws_s3_bucket" "g1_06_log_target" {
  bucket = "g1-06-log-target"
}

resource "aws_s3_bucket_logging" "g1_06" {
  bucket        = aws_s3_bucket.g1_06.id
  target_bucket = aws_s3_bucket.g1_06_log_target.id
  target_prefix = "logs/"
}
