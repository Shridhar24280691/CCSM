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

# TEST: Public access - both clouds properly blocked
# EXPECTED: No cross-cloud finding (consistent)

resource "aws_s3_bucket" "g2_03" {
  bucket = "g2-03-both-blocked"
}

resource "aws_s3_bucket_public_access_block" "g2_03" {
  bucket                  = aws_s3_bucket.g2_03.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "azurerm_storage_account" "g2_03" {
  name                            = "g203bothblocked"
  resource_group_name             = azurerm_resource_group.test.name
  location                        = azurerm_resource_group.test.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false
  public_network_access_enabled   = false
}
