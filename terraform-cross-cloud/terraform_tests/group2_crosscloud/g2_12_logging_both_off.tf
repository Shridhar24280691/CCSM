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

# TEST: Logging - both clouds disabled
# EXPECTED: LOGGING_DISABLED on both, no cross-cloud gap (consistent)

resource "aws_s3_bucket" "g2_12" {
  bucket = "g2-12-log-both-off"
}

resource "azurerm_storage_account" "g2_12" {
  name                     = "g212logbothoff"
  resource_group_name      = azurerm_resource_group.test.name
  location                 = azurerm_resource_group.test.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}
