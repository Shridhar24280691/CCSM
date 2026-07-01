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

# TEST: Logging - AWS enabled, Azure disabled
# EXPECTED: LOGGING_DISABLED on Azure
# EXPECTED: CROSS_CLOUD_LOGGING_GAP

resource "aws_s3_bucket" "g2_09" {
  bucket = "g2-09-log-aws-on"
}

resource "aws_s3_bucket" "g2_09_log_target" {
  bucket = "g2-09-log-target"
}

resource "aws_s3_bucket_logging" "g2_09" {
  bucket        = aws_s3_bucket.g2_09.id
  target_bucket = aws_s3_bucket.g2_09_log_target.id
  target_prefix = "logs/"
}

resource "azurerm_storage_account" "g2_09" {
  name                     = "g209logazureoff"
  resource_group_name      = azurerm_resource_group.test.name
  location                 = azurerm_resource_group.test.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}
