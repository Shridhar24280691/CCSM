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

# TEST: Versioning - both clouds disabled
# EXPECTED: VERSIONING_DISABLED on both, no cross-cloud gap (consistent)

resource "aws_s3_bucket" "g2_08" {
  bucket = "g2-08-version-both-off"
}

resource "azurerm_storage_account" "g2_08" {
  name                     = "g208versionbothoff"
  resource_group_name      = azurerm_resource_group.test.name
  location                 = azurerm_resource_group.test.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  blob_properties {
    versioning_enabled = false
  }
}
