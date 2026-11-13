terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "aws_endpoint" {
  description = "Leave empty for real AWS; set to an emulator URL for local and CI runs"
  type        = string
  default     = ""
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "name_prefix" {
  type    = string
  default = "cloudfiles"
}

locals {
  emulated = var.aws_endpoint != ""
}

provider "aws" {
  region                      = var.region
  access_key                  = local.emulated ? "test" : null
  secret_key                  = local.emulated ? "test" : null
  skip_credentials_validation = local.emulated
  skip_requesting_account_id  = local.emulated
  skip_metadata_api_check     = local.emulated
  s3_use_path_style           = local.emulated

  endpoints {
    s3       = local.emulated ? var.aws_endpoint : null
    dynamodb = local.emulated ? var.aws_endpoint : null
  }
}

resource "aws_s3_bucket" "files" {
  bucket = "${var.name_prefix}-files"
}

resource "aws_s3_bucket_public_access_block" "files" {
  bucket                  = aws_s3_bucket.files.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "files" {
  name         = "${var.name_prefix}-index"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

output "bucket" {
  value = aws_s3_bucket.files.bucket
}

output "table" {
  value = aws_dynamodb_table.files.name
}
