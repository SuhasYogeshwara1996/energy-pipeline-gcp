terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "europe-west3"
}

variable "bucket_name" {
  type = string
}

resource "google_storage_bucket" "raw_landing" {
  name                        = var.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
}

resource "google_bigquery_dataset" "raw" {
  dataset_id = "energy_raw"
  location   = var.region
}

resource "google_bigquery_dataset" "staging" {
  dataset_id = "energy_staging"
  location   = var.region
}

resource "google_bigquery_dataset" "marts" {
  dataset_id = "energy_marts"
  location   = var.region
}

resource "google_service_account" "pipeline_sa" {
  account_id   = "energy-pipeline-sa"
  display_name = "Energy Pipeline Service Account"
}

resource "google_storage_bucket_iam_member" "sa_bucket_access" {
  bucket = google_storage_bucket.raw_landing.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

resource "google_bigquery_dataset_iam_member" "sa_raw_access" {
  dataset_id = google_bigquery_dataset.raw.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

resource "google_bigquery_dataset_iam_member" "sa_staging_access" {
  dataset_id = google_bigquery_dataset.staging.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

resource "google_bigquery_dataset_iam_member" "sa_marts_access" {
  dataset_id = google_bigquery_dataset.marts.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

resource "google_project_iam_member" "sa_job_user" {
  project = "household-energy-consumption"
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}


