terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
    aws     = { source = "hashicorp/aws" }
  }
}

provider "azurerm" {
  features {}
}

provider "aws" {
  region = "eu-west-1"
}

resource "azurerm_resource_group" "test" {
  name     = "rg-test"
  location = "eastus"
}

# TEST: Multiple misconfigurations in one file
# AWS: versioning on, public access blocked, no logging
# Azure: versioning off, public access open, TLS 1.0, no logging
# EXPECTED: Multiple single-cloud findings AND multiple cross-cloud gaps

resource "aws_s3_bucket" "g2_14" {
  bucket = "g2-14-mixed"
}

resource "aws_s3_bucket_versioning" "g2_14" {
  bucket = aws_s3_bucket.g2_14.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "g2_14" {
  bucket                  = aws_s3_bucket.g2_14.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "azurerm_storage_account" "g2_14" {
  name                            = "g214mixed"
  resource_group_name             = azurerm_resource_group.test.name
  location                        = azurerm_resource_group.test.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = true
  min_tls_version                 = "TLS1_0"

  blob_properties {
    versioning_enabled = false
  }
}
