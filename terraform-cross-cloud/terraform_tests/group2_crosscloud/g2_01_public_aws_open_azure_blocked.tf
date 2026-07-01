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

# TEST: Public access - AWS has no block, Azure is properly blocked
# EXPECTED: PUBLIC_ACCESS_NOT_BLOCKED on AWS
# EXPECTED: CROSS_CLOUD_PUBLIC_ACCESS_GAP (Azure blocked but AWS not)

resource "aws_s3_bucket" "g2_01" {
  bucket = "g2-01-public-open"
}

resource "azurerm_storage_account" "g2_01" {
  name                            = "g201publicblocked"
  resource_group_name             = azurerm_resource_group.test.name
  location                        = azurerm_resource_group.test.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false
  public_network_access_enabled   = false
}
