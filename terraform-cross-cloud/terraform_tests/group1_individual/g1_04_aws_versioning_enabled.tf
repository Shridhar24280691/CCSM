terraform {
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
}

provider "aws" {
  region = "eu-west-1"
}

# TEST: AWS bucket with versioning enabled
# EXPECTED: No versioning finding (should pass)

resource "aws_s3_bucket" "g1_04" {
  bucket = "g1-04-versioning-on"
}

resource "aws_s3_bucket_versioning" "g1_04" {
  bucket = aws_s3_bucket.g1_04.id
  versioning_configuration {
    status = "Enabled"
  }
}
