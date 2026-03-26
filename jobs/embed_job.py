"""
Spark Embedding Job — Lawmind document processing pipeline, Stage 2.

Reads OCR JSON output from Stage 1, chunks each document using clause-aware
splitting, generates OpenAI embeddings, and upserts into Qdrant.

Input:  <ocr_output_dir>/*.json  (produced by ocr_job.py)
Output: Qdrant collection (QDRANT_COLLECTION env var, default: mamimind_docs)
        + <embed_output_dir>/*.json  (chunk metadata checkpoint, no vectors)

Environment variables required:
    OPENAI_API_KEY      — for text-embedding-3-small
    QDRANT_URL          — e.g. http://localhost:6333 or http://qdrant:6333
    QDRANT_COLLECTION   — collection name (default: mamimind_docs)

Usage (inside spark-master container):
    spark-submit \\
        --master spark://spark-master:7077 \\
        /app/jobs/embed_job.py \\
        --input  /app/storage/processed/ocr \\
        --output /app/storage/processed/embeddings
"""

import argparse
import os
import re
import uuid
from typing import Iterator, List

from pyspark.sql import SparkSession, Row
from pyspark.sql.functions import col, explode, udf
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, ArrayType,
)


# ── Chunking (mirrors tools/chunking.py logic) ────────────────────────────────

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


# ── Partition-level embedding + Qdrant upsert ─────────────────────────────────

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM   = 1536
BATCH_SIZE  = 100   # OpenAI allows up to 2048; keep small to avoid timeouts
MAX_RETRIES = 3


def _embed_and_index_partition(rows: Iterator[Row]) -> Iterator[Row]:
    """
    Called once per Spark partition.
    Batches chunks, generates embeddings via OpenAI (with retry), upserts to Qdrant.
    Yields one Row per chunk for the output checkpoint.
    """
    import openai
    from tenacity import retry, stop_after_attempt, wait_exponential
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance

    api_key    = os.environ["OPENAI_API_KEY"]
    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    collection = os.environ.get("QDRANT_COLLECTION", "mamimind_docs")

    oai_client = openai.OpenAI(api_key=api_key)
    qdrant     = QdrantClient(url=qdrant_url)

    # Ensure collection exists (idempotent)
    existing = {c.name for c in qdrant.get_collections().collections}
    if collection not in existing:
        qdrant.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )

    # Materialise partition — partitions are small (CHUNK_SIZE chars each)
    batch: List[Row] = list(rows)
    if not batch:
        return

    texts = [row["text"] for row in batch]

    # Embed with exponential-backoff retry (handles OpenAI rate limits)
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _embed_batch(sub_texts: List[str]) -> List[List[float]]:
        response = oai_client.embeddings.create(model=EMBED_MODEL, input=sub_texts)
        return [item.embedding for item in response.data]

    all_embeddings: List[List[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        all_embeddings.extend(_embed_batch(texts[i : i + BATCH_SIZE]))

    # Upsert to Qdrant
    points = [
        PointStruct(
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
        )
        for row, embedding in zip(batch, all_embeddings)
    ]
    qdrant.upsert(collection_name=collection, points=points)

    # Yield checkpoint rows (metadata only — no vectors)
    for row in batch:
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
    parser.add_argument("--input",      required=True, help="OCR output directory (JSON)")
    parser.add_argument("--output",     required=True, help="Output directory for chunk metadata")
    parser.add_argument("--partitions", type=int, default=4, help="Spark partitions (default: 4)")
    args = parser.parse_args()

    spark = SparkSession.builder \
        .appName("LawmindEmbed") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    print(f"[Embed] Input:   {args.input}")
    print(f"[Embed] Output:  {args.output}")
    print(f"[Embed] Qdrant:  {os.environ.get('QDRANT_URL', 'http://localhost:6333')}")

    # ── Step 1: Load successful OCR output ────────────────────────────────────
    ocr_df = spark.read.json(args.input) \
        .filter(col("status") == "success") \
        .filter(col("text").isNotNull() & (col("text") != ""))

    doc_count = ocr_df.count()
    print(f"[Embed] Documents to process: {doc_count}")

    # ── Step 2: Explode into chunks ───────────────────────────────────────────
    chunk_schema = ArrayType(StructType([
        StructField("chunk_id",    StringType(),  nullable=False),
        StructField("chunk_index", IntegerType(), nullable=False),
        StructField("text",        StringType(),  nullable=False),
    ]))

    @udf(chunk_schema)
    def chunk_udf(text, doc_id):
        return _chunk_text(text or "", doc_id or "unknown")

    chunks_df = ocr_df \
        .withColumn("chunks", chunk_udf(col("text"), col("doc_id"))) \
        .withColumn("chunk",  explode(col("chunks"))) \
        .select(
            col("chunk.chunk_id").alias("chunk_id"),
            col("chunk.chunk_index").alias("chunk_index"),
            col("chunk.text").alias("text"),
            col("doc_id"),
            col("user_id"),
            col("filename"),
        ) \
        .repartition(args.partitions) \
        .cache()   # cache so we can count without re-chunking

    chunk_count = chunks_df.count()
    print(f"[Embed] Total chunks to embed: {chunk_count}")

    # ── Step 3: Embed + index via mapPartitions ───────────────────────────────
    # mapPartitions runs exactly once per partition during the write below.
    # Do NOT call result_df.count() after write — that would re-run the embeddings.
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

    # ── Step 4: Write checkpoint (triggers the actual embedding + indexing) ───
    result_df.write.mode("overwrite").json(args.output)

    chunks_df.unpersist()

    print(f"\n[Embed] Done. {chunk_count} chunks from {doc_count} documents indexed into Qdrant.")
    spark.stop()


if __name__ == "__main__":
    main()
