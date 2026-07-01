terraform {
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
}

provider "aws" {
  region = "eu-west-1"
}

# TEST: AWS bucket with no versioning resource
# EXPECTED: VERSIONING_DISABLED finding

resource "aws_s3_bucket" "g1_03" {
  bucket = "g1-03-versioning-off"
}
