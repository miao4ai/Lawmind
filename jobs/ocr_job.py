"""
Spark OCR Job — Lawmind document processing pipeline, Stage 1.

Reads PDF files from an input directory, extracts text with pytesseract,
and writes the results as JSON to an output directory.

Input layout:
    <input_dir>/
        <user_id>/<doc_id>/<filename>.pdf   (local or gs://)

Output layout:
    <output_dir>/
        part-*.json    (one JSON object per PDF)

Each output record:
    {
        "doc_id":      "doc_abc123",
        "user_id":     "user_xyz",
        "source_path": "gs://bucket/raw/user_xyz/doc_abc123/file.pdf",
        "filename":    "file.pdf",
        "text":        "...",
        "page_count":  5,
        "status":      "success" | "failed",
        "error":       null | "error message"
    }

Usage (inside spark-master container):
    spark-submit \\
        --master spark://spark-master:7077 \\
        /app/jobs/ocr_job.py \\
        --input  /app/storage/raw \\
        --output /app/storage/processed/ocr

    # or with GCS:
    spark-submit ... /app/jobs/ocr_job.py \\
        --input  gs://your-bucket/raw \\
        --output gs://your-bucket/processed/ocr
"""

import argparse

from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col
from pyspark.sql.types import StructType, StructField, StringType, IntegerType


# ── OCR logic (runs inside each Spark executor) ───────────────────────────────

def _extract_text_from_pdf(content) -> dict:
    """Extract text from PDF bytes using pdf2image + pytesseract."""
    try:
        from pdf2image import convert_from_bytes
        import pytesseract

        images = convert_from_bytes(bytes(content), dpi=200)
        pages = [pytesseract.image_to_string(img, lang="eng") for img in images]

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

    Works for both local paths and GCS URIs (gs://bucket/raw/user/doc/file.pdf).
    Expected structure: .../raw/<user_id>/<doc_id>/<filename>.pdf
    """
    # Split on "/" — works for both POSIX paths and gs:// URIs
    parts = [p for p in path.split("/") if p and p not in ("gs:", "")]
    try:
        raw_idx = next(i for i, p in enumerate(parts) if p == "raw")
        user_id  = parts[raw_idx + 1]
        doc_id   = parts[raw_idx + 2]
        filename = parts[-1]
    except (StopIteration, IndexError):
        user_id  = "unknown"
        doc_id   = parts[-2] if len(parts) >= 2 else "unknown"
        filename = parts[-1] if parts else "unknown"

    return {"user_id": user_id, "doc_id": doc_id, "filename": filename}


parse_path_schema = StructType([
    StructField("user_id",  StringType(), nullable=False),
    StructField("doc_id",   StringType(), nullable=False),
    StructField("filename", StringType(), nullable=False),
])

parse_path_udf = udf(_parse_path_parts, parse_path_schema)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Lawmind Spark OCR Job")
    parser.add_argument("--input",      required=True, help="Input directory with PDFs (local or gs://)")
    parser.add_argument("--output",     required=True, help="Output directory for OCR results")
    parser.add_argument("--partitions", type=int, default=4, help="Spark partitions (default: 4)")
    args = parser.parse_args()

    spark = SparkSession.builder \
        .appName("LawmindOCR") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    print(f"[OCR] Input:  {args.input}")
    print(f"[OCR] Output: {args.output}")

    # Read all PDFs as binary rows: (path, modificationTime, length, content)
    raw_df = spark.read.format("binaryFile") \
        .option("pathGlobFilter", "*.pdf") \
        .option("recursiveFileLookup", "true") \
        .load(args.input) \
        .repartition(args.partitions)

    # Apply OCR + parse path metadata in one pass, then cache
    result_df = raw_df \
        .withColumn("ocr",   ocr_udf(col("content"))) \
        .withColumn("parts", parse_path_udf(col("path"))) \
        .select(
            col("parts.doc_id").alias("doc_id"),
            col("parts.user_id").alias("user_id"),
            col("parts.filename").alias("filename"),
            col("path").alias("source_path"),
            col("ocr.text").alias("text"),
            col("ocr.page_count").alias("page_count"),
            col("ocr.status").alias("status"),
            col("ocr.error").alias("error"),
        ) \
        .cache()   # cache so counts below don't re-run OCR

    # Count before writing — avoids a second full scan after write
    total   = result_df.count()
    success = result_df.filter(col("status") == "success").count()
    failed  = total - success

    # Write results
    result_df.write.mode("overwrite").json(args.output)
    result_df.unpersist()

    print(f"\n[OCR] Done. Total: {total} | Success: {success} | Failed: {failed}")
    if failed:
        print("[OCR] Failed documents:")
        result_df.filter(col("status") == "failed") \
            .select("doc_id", "source_path", "error") \
            .show(truncate=80)

    spark.stop()


if __name__ == "__main__":
    main()
