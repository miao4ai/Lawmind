"""
Upload legal PDF documents to Google Cloud Storage (GCS).

This script:
1. Reads PDF files from data/source/
2. Uploads them to a specified GCS bucket

Usage:
    python data/upload_to_gcs.py \
        --bucket YOUR_BUCKET_NAME \
        --prefix legal_documents/

Prerequisites:
    pip install google-cloud-storage
    - GCP authentication configured (gcloud auth application-default login)
"""

import argparse
import sys
from pathlib import Path

from google.cloud import storage


SOURCE_DIR = Path(__file__).parent / "source"


def upload_to_gcs(bucket_name: str, source_dir: Path, prefix: str = ""):
    """Upload all PDF files from source_dir to a GCS bucket."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    pdf_files = list(source_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {source_dir}")
        sys.exit(1)

    print(f"Found {len(pdf_files)} PDF file(s) in {source_dir}")
    print(f"Uploading to gs://{bucket_name}/{prefix}")

    for pdf_path in pdf_files:
        blob_name = f"{prefix}{pdf_path.name}" if prefix else pdf_path.name
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(pdf_path))
        print(f"  Uploaded: gs://{bucket_name}/{blob_name} ({pdf_path.stat().st_size / 1024:.1f} KB)")

    print(f"\nDone. {len(pdf_files)} file(s) uploaded.")


def main():
    parser = argparse.ArgumentParser(
        description="Upload legal PDF documents to Google Cloud Storage"
    )
    parser.add_argument("--bucket", required=True, help="GCS bucket name")
    parser.add_argument("--prefix", default="legal_documents/", help="Object name prefix (folder path in GCS)")
    parser.add_argument("--source-dir", default=str(SOURCE_DIR), help="Local directory containing PDF files")
    args = parser.parse_args()

    upload_to_gcs(args.bucket, Path(args.source_dir), args.prefix)


if __name__ == "__main__":
    main()
