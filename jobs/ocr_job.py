"""
Spark OCR Job — Lawmind document processing pipeline, Stage 1.

Reads PDF files from an input directory, extracts text with pytesseract,
and writes the results as JSON-lines to an output directory.

Input layout:
    <input_dir>/
        <user_id>/<doc_id>/<filename>.pdf
        ...

Output layout:
    <output_dir>/
        part-*.jsonl    (one JSON object per PDF)

Each output record:
    {
        "doc_id":     "doc_abc123",
        "user_id":    "user_xyz",
        "source_path": "/app/storage/raw/user_xyz/doc_abc123/file.pdf",
        "filename":   "file.pdf",
        "text":       "...",
        "page_count": 5,
        "status":     "success" | "failed",
        "error":      null | "error message"
    }

Usage (inside spark-master container):
    spark-submit \
        --master spark://spark-master:7077 \
        --conf spark.executor.memory=3g \
        /app/jobs/ocr_job.py \
        --input /app/storage/raw \
        --output /app/storage/processed/ocr
"""

import argparse
import json
import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, input_file_name
from pyspark.sql.types import StructType, StructField, StringType, IntegerType


# ── OCR logic (runs inside each Spark executor) ───────────────────────────────

def _extract_text_from_pdf(content: bytes) -> dict:
    """Extract text from PDF bytes using pdf2image + pytesseract."""
    try:
        from pdf2image import convert_from_bytes
        import pytesseract

        images = convert_from_bytes(content, dpi=200)
        pages = []
        for img in images:
            text = pytesseract.image_to_string(img, lang="eng")
            pages.append(text)

        return {
            "text": "\n\n".join(pages),
            "page_count": len(pages),
            "status": "success",
            "error": None,
        }
    except Exception as exc:
        return {
            "text": "",
            "page_count": 0,
            "status": "failed",
            "error": str(exc),
        }


# ── Spark UDF ─────────────────────────────────────────────────────────────────

ocr_schema = StructType([
    StructField("text",       StringType(),  nullable=True),
    StructField("page_count", IntegerType(), nullable=True),
    StructField("status",     StringType(),  nullable=False),
    StructField("error",      StringType(),  nullable=True),
])

ocr_udf = udf(_extract_text_from_pdf, ocr_schema)


# ── Path helpers ──────────────────────────────────────────────────────────────

def _parse_path_parts(path: str) -> dict:
    """Extract user_id, doc_id, filename from storage path.

    Expected: .../raw/<user_id>/<doc_id>/<filename>.pdf
    """
    parts = Path(path).parts
    try:
        # Find "raw" in the path and take the two segments after it
        raw_idx = next(i for i, p in enumerate(parts) if p == "raw")
        user_id = parts[raw_idx + 1]
        doc_id  = parts[raw_idx + 2]
        filename = parts[-1]
    except (StopIteration, IndexError):
        user_id = "unknown"
        doc_id  = Path(path).parent.name
        filename = Path(path).name

    return {"user_id": user_id, "doc_id": doc_id, "filename": filename}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Lawmind Spark OCR Job")
    parser.add_argument("--input",  required=True, help="Input directory with PDFs")
    parser.add_argument("--output", required=True, help="Output directory for OCR results")
    parser.add_argument("--partitions", type=int, default=4,
                        help="Number of Spark partitions (default: 4)")
    args = parser.parse_args()

    input_path  = args.input.rstrip("/")
    output_path = args.output.rstrip("/")

    spark = SparkSession.builder \
        .appName("LawmindOCR") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    print(f"[OCR] Reading PDFs from: {input_path}")
    print(f"[OCR] Writing results to: {output_path}")

    # Read all PDFs as binary — each row: (path, modificationTime, length, content)
    raw_df = spark.read.format("binaryFile") \
        .option("pathGlobFilter", "*.pdf") \
        .option("recursiveFileLookup", "true") \
        .load(input_path)

    # Repartition for parallelism
    raw_df = raw_df.repartition(args.partitions)

    # Apply OCR
    ocr_df = raw_df.withColumn("ocr", ocr_udf(col("content"))) \
        .select(
            col("path").alias("source_path"),
            col("ocr.text").alias("text"),
            col("ocr.page_count").alias("page_count"),
            col("ocr.status").alias("status"),
            col("ocr.error").alias("error"),
        )

    # Parse user_id, doc_id, filename from path using a Python UDF
    parse_path_schema = StructType([
        StructField("user_id",  StringType(), nullable=False),
        StructField("doc_id",   StringType(), nullable=False),
        StructField("filename", StringType(), nullable=False),
    ])

    @udf(parse_path_schema)
    def parse_path_udf(path):
        return _parse_path_parts(path)

    result_df = ocr_df \
        .withColumn("parts", parse_path_udf(col("source_path"))) \
        .select(
            col("parts.doc_id").alias("doc_id"),
            col("parts.user_id").alias("user_id"),
            col("parts.filename").alias("filename"),
            col("source_path"),
            col("text"),
            col("page_count"),
            col("status"),
            col("error"),
        )

    # Write as JSON lines — one file per partition, easy to read downstream
    result_df.write \
        .mode("overwrite") \
        .json(output_path)

    # Print summary
    total    = result_df.count()
    success  = result_df.filter(col("status") == "success").count()
    failed   = total - success

    print(f"\n[OCR] Done. Total: {total} | Success: {success} | Failed: {failed}")
    if failed:
        print("[OCR] Failed documents:")
        result_df.filter(col("status") == "failed") \
            .select("doc_id", "source_path", "error") \
            .show(truncate=80)

    spark.stop()


if __name__ == "__main__":
    main()
