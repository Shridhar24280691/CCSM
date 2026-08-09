# main.tf
# Live deployment test for the CCSM dissertation
# This deploys a real cross-cloud storage misconfiguration
# to demonstrate the research works on actual cloud resources.
#
# What this creates:
#   AWS:   One S3 bucket WITH versioning enabled
#   Azure: One Storage Account WITHOUT versioning
#
# This is test case g2_05 (versioning gap) deployed for real.
# The CCSM scanner will detect this gap. Checkov and tfsec
# would miss it when scanning either cloud individually.

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

provider "azurerm" {
  features {}
}

# Random suffix to make resource names globally unique
resource "random_id" "suffix" {
  byte_length = 4
}

# Azure Resource Group 
resource "azurerm_resource_group" "thesis" {
  name     = "rg-thesis-ccsm-test"
  location = "Canada Central"
}

# AWS S3 Bucket — versioning ON 
resource "aws_s3_bucket" "thesis_test" {
  bucket = "thesis-ccsm-${random_id.suffix.hex}"

  tags = {
    Project     = "CCSM Thesis"
    Environment = "Test"
    Purpose     = "Cross-cloud misconfiguration research"
  }
}

resource "aws_s3_bucket_versioning" "thesis_test" {
  bucket = aws_s3_bucket.thesis_test.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Block public access on AWS (security best practice)
resource "aws_s3_bucket_public_access_block" "thesis_test" {
  bucket                  = aws_s3_bucket.thesis_test.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Azure Storage Account — versioning OFF 
# This is the deliberate cross-cloud inconsistency
# AWS has versioning ON, Azure has it OFF
resource "azurerm_storage_account" "thesis_test" {
  name                     = "thesisccsm${random_id.suffix.hex}"
  resource_group_name      = azurerm_resource_group.thesis.name
  location                 = azurerm_resource_group.thesis.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # Versioning deliberately disabled to create cross-cloud gap
  blob_properties {
    versioning_enabled = false
  }

  tags = {
    Project     = "CCSM Thesis"
    Environment = "Test"
    Purpose     = "Cross-cloud misconfiguration research"
  }
}

# Outputs
output "aws_bucket_name" {
  description = "The name of the AWS S3 bucket created"
  value       = aws_s3_bucket.thesis_test.bucket
}

output "aws_bucket_arn" {
  description = "The ARN of the AWS S3 bucket"
  value       = aws_s3_bucket.thesis_test.arn
}

output "azure_storage_account_name" {
  description = "The name of the Azure Storage Account created"
  value       = azurerm_storage_account.thesis_test.name
}

output "azure_resource_group" {
  description = "The Azure resource group containing the storage account"
  value       = azurerm_resource_group.thesis.name
}