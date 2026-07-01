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

# TEST: TLS - Azure uses TLS 1.0 which is insecure
# EXPECTED: TLS_VERSION_LOW on Azure

resource "aws_s3_bucket" "g2_13" {
  bucket = "g2-13-tls-test"
}

resource "azurerm_storage_account" "g2_13" {
  name                     = "g213tlslow"
  resource_group_name      = azurerm_resource_group.test.name
  location                 = azurerm_resource_group.test.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_0"
}
