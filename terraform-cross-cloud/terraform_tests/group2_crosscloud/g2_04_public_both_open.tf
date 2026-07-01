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

# TEST: Public access - both clouds allow public access
# EXPECTED: PUBLIC_ACCESS_NOT_BLOCKED on both, no cross-cloud gap (consistent)

resource "aws_s3_bucket" "g2_04" {
  bucket = "g2-04-both-open"
}

resource "azurerm_storage_account" "g2_04" {
  name                            = "g204bothopen"
  resource_group_name             = azurerm_resource_group.test.name
  location                        = azurerm_resource_group.test.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = true
}
