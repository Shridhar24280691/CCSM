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

# TEST: Versioning - both clouds enabled
# EXPECTED: No cross-cloud finding (consistent)

resource "aws_s3_bucket" "g2_07" {
  bucket = "g2-07-version-both-on"
}

resource "aws_s3_bucket_versioning" "g2_07" {
  bucket = aws_s3_bucket.g2_07.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "azurerm_storage_account" "g2_07" {
  name                     = "g207versionbothon"
  resource_group_name      = azurerm_resource_group.test.name
  location                 = azurerm_resource_group.test.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  blob_properties {
    versioning_enabled = true
  }
}
