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

# TEST: Versioning - AWS enabled, Azure disabled
# EXPECTED: VERSIONING_DISABLED on Azure
# EXPECTED: CROSS_CLOUD_VERSIONING_GAP

resource "aws_s3_bucket" "g2_05" {
  bucket = "g2-05-version-aws-on"
}

resource "aws_s3_bucket_versioning" "g2_05" {
  bucket = aws_s3_bucket.g2_05.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "azurerm_storage_account" "g2_05" {
  name                     = "g205versionazureoff"
  resource_group_name      = azurerm_resource_group.test.name
  location                 = azurerm_resource_group.test.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  blob_properties {
    versioning_enabled = false
  }
}
