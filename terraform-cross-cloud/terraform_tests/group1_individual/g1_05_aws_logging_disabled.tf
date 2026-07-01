terraform {
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
}

provider "aws" {
  region = "eu-west-1"
}

# TEST: AWS bucket with no logging resource
# EXPECTED: LOGGING_DISABLED finding

resource "aws_s3_bucket" "g1_05" {
  bucket = "g1-05-logging-off"
}
