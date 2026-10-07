import argparse
import zipfile
from pathlib import Path

import requests
from google.cloud import bigquery, storage

UCI_ZIP_URL = (
    "https://archive.ics.uci.edu/static/public/235/"
    "individual+household+electric+power+consumption.zip"
)
RAW_FILENAME = "household_power_consumption.txt"
LOCAL_DIR = Path("data")
LOCAL_DIR.mkdir(exist_ok=True)


def download_and_extract() -> Path:
    """Download the UCI zip and extract the raw .txt file locally."""
    local_zip_path = LOCAL_DIR / "household_power_consumption.zip"
    local_txt_path = LOCAL_DIR / RAW_FILENAME

    if local_txt_path.exists():
        print(f"Already downloaded: {local_txt_path}")
        return local_txt_path

    print(f"Downloading from {UCI_ZIP_URL} ...")
    response = requests.get(UCI_ZIP_URL, timeout=120)
    response.raise_for_status()
    local_zip_path.write_bytes(response.content)

    print("Extracting ...")
    with zipfile.ZipFile(local_zip_path) as zf:
        zf.extract(RAW_FILENAME, LOCAL_DIR)

    print(f"Saved raw file to {local_txt_path}")
    return local_txt_path


def clean_raw_file(local_path: Path) -> Path:
    """The source file mixes two styles of missing value: the documented '?'
    marker, and some rows with a truly empty field (nothing between two
    semicolons). BigQuery's null_marker only recognizes one string, so we
    normalize both to '?' before loading. Writes a new file rather than
    overwriting the original, so the untouched raw download is preserved."""
    cleaned_path = local_path.with_name("household_power_consumption_clean.txt")

    with open(local_path, "r", encoding="utf-8") as fin, \
         open(cleaned_path, "w", encoding="utf-8") as fout:
        header = fin.readline()
        fout.write(header)
        for line in fin:
            fields = line.rstrip("\n").split(";")
            fields = [f if f != "" else "?" for f in fields]
            fout.write(";".join(fields) + "\n")

    print(f"Cleaned file written to {cleaned_path}")
    return cleaned_path


def upload_to_gcs(local_path: Path, bucket_name: str) -> str:
    """Upload the file to the GCS landing bucket. Returns the GCS URI."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob_name = f"raw/{local_path.name}"
    blob = bucket.blob(blob_name)

    # Smaller chunks + longer timeout handle unstable connections better
    # than one giant request for a ~130MB file.
    blob.chunk_size = 5 * 1024 * 1024  # 5MB per chunk

    print(f"Uploading to gs://{bucket_name}/{blob_name} ...")
    blob.upload_from_filename(str(local_path), timeout=600)

    gcs_uri = f"gs://{bucket_name}/{blob_name}"
    print(f"Uploaded: {gcs_uri}")
    return gcs_uri


def load_into_bigquery(gcs_uri: str, project_id: str) -> None:
    """Load the cleaned file from GCS into a BigQuery table in energy_raw."""
    client = bigquery.Client(project=project_id)
    table_id = f"{project_id}.energy_raw.household_power_consumption"

    # The source file is semicolon-delimited with "?" for missing values
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        field_delimiter=";",
        skip_leading_rows=1,
        autodetect=False,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        null_marker="?",
        schema=[
            bigquery.SchemaField("Date", "STRING"),
            bigquery.SchemaField("Time", "STRING"),
            bigquery.SchemaField("Global_active_power", "FLOAT64"),
            bigquery.SchemaField("Global_reactive_power", "FLOAT64"),
            bigquery.SchemaField("Voltage", "FLOAT64"),
            bigquery.SchemaField("Global_intensity", "FLOAT64"),
            bigquery.SchemaField("Sub_metering_1", "FLOAT64"),
            bigquery.SchemaField("Sub_metering_2", "FLOAT64"),
            bigquery.SchemaField("Sub_metering_3", "FLOAT64"),
        ],
    )

    print(f"Loading {gcs_uri} into {table_id} ...")
    load_job = client.load_table_from_uri(gcs_uri, table_id, job_config=job_config)
    load_job.result()  # wait for the job to finish

    table = client.get_table(table_id)
    print(f"Loaded {table.num_rows:,} rows into {table_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--bucket", required=True, help="GCS bucket name (the raw landing bucket)")
    args = parser.parse_args()

    local_path = download_and_extract()
    local_path = clean_raw_file(local_path)
    gcs_uri = upload_to_gcs(local_path, args.bucket)
    load_into_bigquery(gcs_uri, args.project)
    print("\nDone. Raw data is now in BigQuery at energy_raw.household_power_consumption")


if __name__ == "__main__":
    main()