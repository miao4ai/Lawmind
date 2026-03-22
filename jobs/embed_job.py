"""
Spark Embedding Job — Lawmind document processing pipeline, Stage 2.

Reads OCR JSON output from Stage 1, chunks each document using clause-aware
splitting (matching tools/chunking.py logic), generates OpenAI embeddings,
and upserts the results into Qdrant.

Input:  <ocr_output_dir>/*.json  (produced by ocr_job.py)
Output: Qdrant collection (QDRANT_COLLECTION env var, default: mamimind_docs)
        + <embed_output_dir>/*.json  (checkpoint — chunk metadata without vectors)

Environment variables required:
    OPENAI_API_KEY      — for text-embedding-3-small
    QDRANT_URL          — e.g. http://localhost:6333 or http://qdrant:6333
    QDRANT_COLLECTION   — collection name (default: mamimind_docs)

Usage (inside spark-master container):
    spark-submit \
        --master spark://spark-master:7077 \
        --conf spark.executor.memory=3g \
        /app/jobs/embed_job.py \
        --input  /app/storage/processed/ocr \
        --output /app/storage/processed/embeddings
"""

import argparse
import json
import os
import re
import uuid
from typing import Iterator, List

from pyspark.sql import SparkSession, Row
from pyspark.sql.functions import col, explode
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    ArrayType, FloatType,
)


# ── Chunking (mirrors tools/chunking.py — inlined to avoid import path issues) ─

CLAUSE_PATTERN = re.compile(
    r"(\n\s*(?:\d+\.(?:\d+\.?)*|\(?[a-z]\)|Article\s+\d+|Section\s+\d+))"
)
CHUNK_SIZE    = 500
CHUNK_OVERLAP = 50


def _chunk_text(text: str, doc_id: str) -> List[dict]:
    """Clause-aware chunking — returns list of chunk dicts."""
    parts   = CLAUSE_PATTERN.split(text)
    chunks  = []
    current = ""
    idx     = 0

    for part in parts:
        if len(current) + len(part) > CHUNK_SIZE:
            if current.strip():
                chunks.append({
                    "chunk_id":    f"{doc_id}_{idx}",
                    "chunk_index": idx,
                    "text":        current.strip(),
                })
                idx += 1
            current = part
        else:
            current += part

    if current.strip():
        chunks.append({
            "chunk_id":    f"{doc_id}_{idx}",
            "chunk_index": idx,
            "text":        current.strip(),
        })

    return chunks


# ── Partition-level embedding + Qdrant upsert ──────────────────────────────────

EMBED_MODEL   = "text-embedding-3-small"
EMBED_DIM     = 1536
BATCH_SIZE    = 100   # OpenAI allows up to 2048; keep small to avoid timeouts


def _embed_and_index_partition(rows: Iterator[Row]) -> Iterator[Row]:
    """
    Called once per Spark partition.
    Batches chunks, generates embeddings via OpenAI, upserts to Qdrant.
    Yields one Row per chunk (for the output checkpoint).
    """
    import openai
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance

    api_key        = os.environ["OPENAI_API_KEY"]
    qdrant_url     = os.environ.get("QDRANT_URL", "http://localhost:6333")
    collection     = os.environ.get("QDRANT_COLLECTION", "mamimind_docs")

    oai_client = openai.OpenAI(api_key=api_key)
    qdrant     = QdrantClient(url=qdrant_url)

    # Ensure collection exists
    existing = [c.name for c in qdrant.get_collections().collections]
    if collection not in existing:
        qdrant.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )

    # Accumulate all rows from this partition into memory
    # (partitions are sized small enough — ~CHUNK_SIZE chars each)
    batch: List[Row] = list(rows)
    if not batch:
        return

    # Build text list and metadata
    texts    = [row["text"] for row in batch]
    metadatas = batch  # keep reference

    # Generate embeddings in sub-batches
    all_embeddings: List[List[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        sub_texts = texts[i : i + BATCH_SIZE]
        response  = oai_client.embeddings.create(model=EMBED_MODEL, input=sub_texts)
        all_embeddings.extend([item.embedding for item in response.data])

    # Upsert to Qdrant
    points = []
    for row, embedding in zip(metadatas, all_embeddings):
        points.append(PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, row["chunk_id"])),
            vector=embedding,
            payload={
                "chunk_id":    row["chunk_id"],
                "doc_id":      row["doc_id"],
                "user_id":     row["user_id"],
                "text":        row["text"],
                "chunk_index": row["chunk_index"],
                "metadata": {
                    "doc_id":   row["doc_id"],
                    "user_id":  row["user_id"],
                    "filename": row["filename"],
                },
            },
        ))

    qdrant.upsert(collection_name=collection, points=points)

    # Yield checkpoint rows (no vectors — just metadata)
    for row in metadatas:
        yield Row(
            chunk_id    = row["chunk_id"],
            doc_id      = row["doc_id"],
            user_id     = row["user_id"],
            filename    = row["filename"],
            chunk_index = row["chunk_index"],
            text        = row["text"],
            status      = "indexed",
        )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Lawmind Spark Embedding Job")
    parser.add_argument("--input",  required=True, help="OCR output directory (JSON)")
    parser.add_argument("--output", required=True, help="Output directory for chunk metadata")
    parser.add_argument("--partitions", type=int, default=4,
                        help="Spark partitions (default: 4)")
    args = parser.parse_args()

    spark = SparkSession.builder \
        .appName("LawmindEmbed") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    print(f"[Embed] Reading OCR output from: {args.input}")
    print(f"[Embed] Writing chunk metadata to: {args.output}")
    print(f"[Embed] Qdrant: {os.environ.get('QDRANT_URL', 'http://localhost:6333')}")

    # ── Step 1: Load OCR output ──────────────────────────────────────────────
    ocr_df = spark.read.json(args.input) \
        .filter(col("status") == "success") \
        .filter(col("text").isNotNull() & (col("text") != ""))

    doc_count = ocr_df.count()
    print(f"[Embed] Loaded {doc_count} successfully OCR'd documents")

    # ── Step 2: Explode into chunks (driver-side UDF via mapInPandas-lite) ───
    # Use a regular UDF to produce an array of chunk structs per document.

    chunk_schema = ArrayType(StructType([
        StructField("chunk_id",    StringType(),  nullable=False),
        StructField("chunk_index", IntegerType(), nullable=False),
        StructField("text",        StringType(),  nullable=False),
    ]))

    from pyspark.sql.functions import udf as spark_udf

    @spark_udf(chunk_schema)
    def chunk_udf(text, doc_id):
        return _chunk_text(text or "", doc_id or "unknown")

    chunks_df = ocr_df \
        .withColumn("chunks", chunk_udf(col("text"), col("doc_id"))) \
        .withColumn("chunk", explode(col("chunks"))) \
        .select(
            col("chunk.chunk_id").alias("chunk_id"),
            col("chunk.chunk_index").alias("chunk_index"),
            col("chunk.text").alias("text"),
            col("doc_id"),
            col("user_id"),
            col("filename"),
        ) \
        .repartition(args.partitions)

    chunk_count = chunks_df.count()
    print(f"[Embed] Total chunks to embed: {chunk_count}")

    # ── Step 3: Embed + index (one partition = one batch of API calls) ───────
    result_schema = StructType([
        StructField("chunk_id",    StringType(),  nullable=False),
        StructField("doc_id",      StringType(),  nullable=False),
        StructField("user_id",     StringType(),  nullable=False),
        StructField("filename",    StringType(),  nullable=True),
        StructField("chunk_index", IntegerType(), nullable=False),
        StructField("text",        StringType(),  nullable=False),
        StructField("status",      StringType(),  nullable=False),
    ])

    result_rdd = chunks_df.rdd.mapPartitions(_embed_and_index_partition)
    result_df  = spark.createDataFrame(result_rdd, schema=result_schema)

    # ── Step 4: Save chunk metadata checkpoint ────────────────────────────────
    result_df.write.mode("overwrite").json(args.output)

    indexed_count = result_df.count()
    print(f"\n[Embed] Done. Indexed {indexed_count} / {chunk_count} chunks into Qdrant.")

    spark.stop()


if __name__ == "__main__":
    main()
