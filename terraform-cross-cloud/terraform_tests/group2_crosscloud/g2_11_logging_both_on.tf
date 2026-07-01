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

# TEST: Logging - both clouds enabled
# EXPECTED: No cross-cloud finding (consistent)

resource "aws_s3_bucket" "g2_11" {
  bucket = "g2-11-log-both-on"
}

resource "aws_s3_bucket" "g2_11_log_target" {
  bucket = "g2-11-log-target"
}

resource "aws_s3_bucket_logging" "g2_11" {
  bucket        = aws_s3_bucket.g2_11.id
  target_bucket = aws_s3_bucket.g2_11_log_target.id
  target_prefix = "logs/"
}

resource "azurerm_storage_account" "g2_11" {
  name                     = "g211logbothon"
  resource_group_name      = azurerm_resource_group.test.name
  location                 = azurerm_resource_group.test.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  blob_properties {
    logging {
      delete                = true
      read                  = true
      write                 = true
      version               = "1.0"
      retention_policy_days = 7
    }
  }
}
