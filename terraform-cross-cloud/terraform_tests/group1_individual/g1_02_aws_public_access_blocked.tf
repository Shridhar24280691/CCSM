terraform {
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
}

provider "aws" {
  region = "eu-west-1"
}

# TEST: AWS bucket with public access properly blocked
# EXPECTED: No public access finding (should pass)

resource "aws_s3_bucket" "g1_02" {
  bucket = "g1-02-public-blocked"
}

resource "aws_s3_bucket_public_access_block" "g1_02" {
  bucket                  = aws_s3_bucket.g1_02.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
