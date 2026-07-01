terraform {
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
}

provider "aws" {
  region = "eu-west-1"
}

# TEST: AWS bucket with no public access block
# EXPECTED: PUBLIC_ACCESS_NOT_BLOCKED finding

resource "aws_s3_bucket" "g1_01" {
  bucket = "g1-01-public-open"
}
