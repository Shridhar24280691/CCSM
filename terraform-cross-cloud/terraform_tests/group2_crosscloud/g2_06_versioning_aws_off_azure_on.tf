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

# TEST: Versioning - AWS disabled, Azure enabled
# EXPECTED: VERSIONING_DISABLED on AWS
# EXPECTED: CROSS_CLOUD_VERSIONING_GAP

resource "aws_s3_bucket" "g2_06" {
  bucket = "g2-06-version-aws-off"
}

resource "azurerm_storage_account" "g2_06" {
  name                     = "g206versionazureon"
  resource_group_name      = azurerm_resource_group.test.name
  location                 = azurerm_resource_group.test.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  blob_properties {
    versioning_enabled = true
  }
}
