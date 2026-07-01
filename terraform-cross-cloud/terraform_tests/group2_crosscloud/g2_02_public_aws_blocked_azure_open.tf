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

# TEST: Public access - AWS is blocked, Azure allows public access
# EXPECTED: PUBLIC_ACCESS_NOT_BLOCKED on Azure
# EXPECTED: CROSS_CLOUD_PUBLIC_ACCESS_GAP (AWS blocked but Azure not)

resource "aws_s3_bucket" "g2_02" {
  bucket = "g2-02-public-blocked"
}

resource "aws_s3_bucket_public_access_block" "g2_02" {
  bucket                  = aws_s3_bucket.g2_02.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "azurerm_storage_account" "g2_02" {
  name                            = "g202publicopen"
  resource_group_name             = azurerm_resource_group.test.name
  location                        = azurerm_resource_group.test.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = true
}
