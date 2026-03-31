"""
Spark Analysis Job — Lawmind document processing pipeline, Stage 1.5.

Runs between OCR (Stage 1) and Embedding (Stage 2).
Reads OCR JSON output, computes data quality metrics, and writes:
  - A per-document quality report (flagging suspicious docs)
  - A corpus-level summary JSON

Run this before embed_job.py to:
  - Catch OCR failures early (before spending OpenAI API budget)
  - Understand text length distribution (tune chunk size)
  - Identify docs that need re-OCR or manual review
  - Estimate embedding API cost (chunk count × token cost)

Output layout:
    <output_dir>/
        summary.json        — corpus-level stats (single file)
        doc_report/         — per-doc quality flags (partitioned JSON)

Usage (inside spark-master container):
    spark-submit \\
        --master spark://spark-master:7077 \\
        /app/jobs/analyze_job.py \\
        --input  /app/storage/processed/ocr \\
        --output /app/storage/processed/analysis

    # or with GCS:
    spark-submit ... /app/jobs/analyze_job.py \\
        --input  gs://your-bucket/processed/ocr \\
        --output gs://your-bucket/processed/analysis
"""

import argparse
import json
import os
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, FloatType, BooleanType,
)


# ── Quality thresholds ────────────────────────────────────────────────────────

# Docs with fewer characters than this are likely blank / bad OCR
MIN_TEXT_CHARS = 100

# Ratio of non-alphanumeric characters above this suggests garbled OCR
MAX_NOISE_RATIO = 0.4

# Estimated average tokens per character (for cost estimation)
CHARS_PER_TOKEN = 4.0

# OpenAI text-embedding-3-small cost per 1M tokens (USD, as of 2024)
COST_PER_1M_TOKENS = 0.02

# Chunk size used in embed_job.py (must match CHUNK_SIZE there)
CHUNK_SIZE = 500


# ── Per-document quality UDF ──────────────────────────────────────────────────

quality_schema = StructType([
    StructField("text_length",   IntegerType(), nullable=False),
    StructField("word_count",    IntegerType(), nullable=False),
    StructField("noise_ratio",   FloatType(),   nullable=False),
    StructField("est_chunks",    IntegerType(), nullable=False),
    StructField("is_empty",      BooleanType(), nullable=False),
    StructField("is_noisy",      BooleanType(), nullable=False),
    StructField("needs_review",  BooleanType(), nullable=False),
    StructField("review_reason", StringType(),  nullable=True),
])


def _assess_quality(text: str, page_count: int, status: str) -> dict:
    """Compute quality metrics for a single document's OCR text."""
    if status != "success" or not text:
        return {
            "text_length":   0,
            "word_count":    0,
            "noise_ratio":   0.0,
            "est_chunks":    0,
            "is_empty":      True,
            "is_noisy":      False,
            "needs_review":  True,
            "review_reason": f"ocr_failed: {status}",
        }

    text_length = len(text)
    words       = text.split()
    word_count  = len(words)

    # Noise ratio: fraction of chars that are neither alphanumeric nor whitespace
    non_alnum = sum(1 for c in text if not c.isalnum() and not c.isspace())
    noise_ratio = round(non_alnum / max(text_length, 1), 3)

    # Estimated chunk count (rough: text_length / CHUNK_SIZE with some overlap)
    est_chunks = max(1, int(text_length / CHUNK_SIZE * 1.1))

    is_empty     = text_length < MIN_TEXT_CHARS
    is_noisy     = noise_ratio > MAX_NOISE_RATIO
    needs_review = is_empty or is_noisy

    review_reason = None
    if is_empty and is_noisy:
        review_reason = "empty_and_noisy"
    elif is_empty:
        review_reason = f"too_short ({text_length} chars)"
    elif is_noisy:
        review_reason = f"high_noise ({noise_ratio:.0%} non-alnum)"

    return {
        "text_length":   text_length,
        "word_count":    word_count,
        "noise_ratio":   noise_ratio,
        "est_chunks":    est_chunks,
        "is_empty":      is_empty,
        "is_noisy":      is_noisy,
        "needs_review":  needs_review,
        "review_reason": review_reason,
    }


from pyspark.sql.functions import udf as spark_udf

assess_quality_udf = spark_udf(_assess_quality, quality_schema)


# ── Summary helpers ───────────────────────────────────────────────────────────

def _write_summary(summary: dict, output_dir: str, spark: SparkSession) -> None:
    """Write corpus summary as a single JSON file."""
    summary_path = output_dir.rstrip("/") + "/summary.json"

    # Write via Spark so it works for both local and GCS paths
    summary_df = spark.createDataFrame([summary])
    summary_df.coalesce(1).write.mode("overwrite").json(
        output_dir.rstrip("/") + "/summary"
    )


def _print_summary(summary: dict) -> None:
    """Print a human-readable summary to stdout."""
    sep = "─" * 60
    print(f"\n{sep}")
    print("  CORPUS ANALYSIS SUMMARY")
    print(sep)
    print(f"  Documents total:       {summary['total_docs']:>8,}")
    print(f"  OCR success:           {summary['success_docs']:>8,}  "
          f"({summary['success_rate_pct']:.1f}%)")
    print(f"  OCR failed:            {summary['failed_docs']:>8,}")
    print(f"  Needs review:          {summary['needs_review_docs']:>8,}")
    print(sep)
    print(f"  Total pages:           {summary['total_pages']:>8,}")
    print(f"  Avg pages / doc:       {summary['avg_pages_per_doc']:>8.1f}")
    print(sep)
    print(f"  Avg text length:       {summary['avg_text_length']:>8,.0f} chars")
    print(f"  Median text length:    {summary['p50_text_length']:>8,.0f} chars")
    print(f"  p95 text length:       {summary['p95_text_length']:>8,.0f} chars")
    print(sep)
    print(f"  Est. total chunks:     {summary['est_total_chunks']:>8,}")
    print(f"  Est. tokens:           {summary['est_total_tokens']:>8,.0f}")
    print(f"  Est. embedding cost:   ${summary['est_cost_usd']:>7.4f}  "
          f"(text-embedding-3-small)")
    print(sep)
    if summary['needs_review_docs'] > 0:
        print(f"  ⚠  {summary['needs_review_docs']} doc(s) flagged — "
              "check doc_report/ for details")
    else:
        print("  ✓  All documents passed quality checks")
    print(sep + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Lawmind Spark Analysis Job")
    parser.add_argument("--input",  required=True,
                        help="OCR output directory (JSON from ocr_job.py)")
    parser.add_argument("--output", required=True,
                        help="Output directory for analysis results")
    parser.add_argument("--partitions", type=int, default=4,
                        help="Spark partitions (default: 4)")
    args = parser.parse_args()

    spark = SparkSession.builder \
        .appName("LawmindAnalyze") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    print(f"[Analyze] Input:  {args.input}")
    print(f"[Analyze] Output: {args.output}")

    # ── Load OCR output ───────────────────────────────────────────────────────
    ocr_df = spark.read.json(args.input).repartition(args.partitions)
    total_docs = ocr_df.count()

    if total_docs == 0:
        print("[Analyze] No documents found. Check OCR output path.")
        spark.stop()
        return

    # ── Per-document quality assessment ───────────────────────────────────────
    doc_df = ocr_df \
        .withColumn("q", assess_quality_udf(
            F.col("text"),
            F.col("page_count"),
            F.col("status"),
        )) \
        .select(
            F.col("doc_id"),
            F.col("user_id"),
            F.col("filename"),
            F.col("status").alias("ocr_status"),
            F.col("page_count"),
            F.col("q.text_length").alias("text_length"),
            F.col("q.word_count").alias("word_count"),
            F.col("q.noise_ratio").alias("noise_ratio"),
            F.col("q.est_chunks").alias("est_chunks"),
            F.col("q.is_empty").alias("is_empty"),
            F.col("q.is_noisy").alias("is_noisy"),
            F.col("q.needs_review").alias("needs_review"),
            F.col("q.review_reason").alias("review_reason"),
        ) \
        .cache()

    # ── Corpus-level aggregations ─────────────────────────────────────────────
    agg = doc_df.agg(
        F.count("*").alias("total_docs"),
        F.sum(F.when(F.col("ocr_status") == "success", 1).otherwise(0)).alias("success_docs"),
        F.sum(F.when(F.col("ocr_status") != "success", 1).otherwise(0)).alias("failed_docs"),
        F.sum(F.when(F.col("needs_review"), 1).otherwise(0)).alias("needs_review_docs"),
        F.sum("page_count").alias("total_pages"),
        F.avg("page_count").alias("avg_pages_per_doc"),
        F.avg("text_length").alias("avg_text_length"),
        F.percentile_approx("text_length", 0.50).alias("p50_text_length"),
        F.percentile_approx("text_length", 0.95).alias("p95_text_length"),
        F.avg("word_count").alias("avg_word_count"),
        F.avg("noise_ratio").alias("avg_noise_ratio"),
        F.sum("est_chunks").alias("est_total_chunks"),
    ).collect()[0]

    success_docs     = int(agg["success_docs"] or 0)
    est_total_chunks = int(agg["est_total_chunks"] or 0)
    est_total_chars  = float(agg["avg_text_length"] or 0) * success_docs
    est_total_tokens = est_total_chars / CHARS_PER_TOKEN
    est_cost_usd     = (est_total_tokens / 1_000_000) * COST_PER_1M_TOKENS

    summary = {
        "total_docs":         int(agg["total_docs"]),
        "success_docs":       success_docs,
        "failed_docs":        int(agg["failed_docs"] or 0),
        "needs_review_docs":  int(agg["needs_review_docs"] or 0),
        "success_rate_pct":   round(success_docs / max(int(agg["total_docs"]), 1) * 100, 1),
        "total_pages":        int(agg["total_pages"] or 0),
        "avg_pages_per_doc":  round(float(agg["avg_pages_per_doc"] or 0), 1),
        "avg_text_length":    round(float(agg["avg_text_length"] or 0), 0),
        "p50_text_length":    int(agg["p50_text_length"] or 0),
        "p95_text_length":    int(agg["p95_text_length"] or 0),
        "avg_word_count":     round(float(agg["avg_word_count"] or 0), 0),
        "avg_noise_ratio":    round(float(agg["avg_noise_ratio"] or 0), 3),
        "est_total_chunks":   est_total_chunks,
        "est_total_tokens":   round(est_total_tokens, 0),
        "est_cost_usd":       round(est_cost_usd, 4),
    }

    # ── Per-user breakdown ────────────────────────────────────────────────────
    user_breakdown = doc_df \
        .groupBy("user_id") \
        .agg(
            F.count("*").alias("doc_count"),
            F.sum("est_chunks").alias("est_chunks"),
            F.sum(F.when(F.col("needs_review"), 1).otherwise(0)).alias("flagged"),
        ) \
        .orderBy(F.col("doc_count").desc())

    # ── Write outputs ─────────────────────────────────────────────────────────
    output = args.output.rstrip("/")

    # Per-doc quality report (only flagged + failed docs to keep output small)
    doc_df.write.mode("overwrite").json(f"{output}/doc_report")

    # Corpus summary (via Spark for GCS compatibility)
    spark.createDataFrame([summary]) \
        .coalesce(1) \
        .write.mode("overwrite").json(f"{output}/summary")

    # ── Print to console ──────────────────────────────────────────────────────
    _print_summary(summary)

    print("[Analyze] Per-user breakdown:")
    user_breakdown.show(truncate=False)

    flagged = doc_df.filter(F.col("needs_review"))
    if flagged.count() > 0:
        print("[Analyze] Flagged documents (needs review):")
        flagged.select(
            "doc_id", "filename", "ocr_status",
            "text_length", "noise_ratio", "review_reason",
        ).show(50, truncate=60)

    doc_df.unpersist()
    spark.stop()


if __name__ == "__main__":
    main()
