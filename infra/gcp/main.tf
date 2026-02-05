# Terraform configuration for Mamimind GCP infrastructure

terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "mamimind-terraform-state"
    prefix = "terraform/state"
  }
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (dev/staging/prod)"
  type        = string
  default     = "dev"
}

# Provider
provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudscheduler.googleapis.com",
    "pubsub.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudtrace.googleapis.com",
    "logging.googleapis.com",
    "aiplatform.googleapis.com",
  ])

  service            = each.key
  disable_on_destroy = false
}

# Cloud Storage Bucket
resource "google_storage_bucket" "documents" {
  name          = "${var.project_id}-documents-${var.environment}"
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  cors {
    origin          = ["*"]
    method          = ["GET", "PUT", "POST"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
}

# Pub/Sub Topics
resource "google_pubsub_topic" "ocr_process" {
  name = "ocr-process-${var.environment}"

  message_retention_duration = "604800s" # 7 days
}

resource "google_pubsub_topic" "index_doc" {
  name = "index-doc-${var.environment}"

  message_retention_duration = "604800s"
}

# Firestore Database (already exists, just configure)
resource "google_firestore_database" "database" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.apis]
}

# Service Account for Cloud Functions
resource "google_service_account" "function_sa" {
  account_id   = "mamimind-functions-${var.environment}"
  display_name = "Mamimind Cloud Functions Service Account"
}

# IAM Roles for Service Account
resource "google_project_iam_member" "function_permissions" {
  for_each = toset([
    "roles/storage.objectAdmin",
    "roles/datastore.user",
    "roles/pubsub.publisher",
    "roles/cloudtrace.agent",
    "roles/logging.logWriter",
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.function_sa.email}"
}

# Secret Manager for API keys
resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "openai-api-key-${var.environment}"

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret" "qdrant_api_key" {
  secret_id = "qdrant-api-key-${var.environment}"

  replication {
    automatic = true
  }
}

# Outputs
output "storage_bucket" {
  value = google_storage_bucket.documents.name
}

output "pubsub_topics" {
  value = {
    ocr_process = google_pubsub_topic.ocr_process.name
    index_doc   = google_pubsub_topic.index_doc.name
  }
}

output "service_account_email" {
  value = google_service_account.function_sa.email
}
