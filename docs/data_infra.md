# Local Data Infrastructure with Spark + Airflow + GKE

## Overview

This document describes the local data engineering infrastructure for Lawmind, designed to handle large-scale document processing with Apache Spark, orchestrated by Apache Airflow, and connected to GCP via GKE.

The goal is a **hybrid local/cloud setup**: develop and test locally, then seamlessly submit jobs to GKE for production scale.

---

## Architecture

```
Local Development (Docker Compose)              GCP Cloud
┌────────────────────────────────────┐          ┌─────────────────────────┐
│  Airflow                           │  ──────▶  │  GKE Cluster            │
│  (scheduler + webserver + worker)  │          │  (Spark on Kubernetes)  │
│                                    │          │                         │
│  Spark (local mode)                │          │  Cloud Composer         │
│  (dev / unit test)                 │          │  (managed Airflow, opt) │
│                                    │          │                         │
│  MinIO (GCS emulator)              │  ◀─────▶  │  GCS (real storage)     │
│  Qdrant (local)                    │          │  Qdrant / Vertex AI     │
└────────────────────────────────────┘          └─────────────────────────┘
          │ kubeconfig switch
          └──────────────────────────────────────────────────────────────┘
                         Shared GCS as the data layer
```

### How local and cloud connect

- **Storage**: MinIO locally emulates GCS with the same S3-compatible API. Switching to real GCS requires only a config change (connection string).
- **Kubernetes**: `kubectl` context points to local Docker Desktop or GKE. Airflow `KubernetesPodOperator` and `SparkKubernetesOperator` submit jobs to whichever context is active.
- **Airflow connections**: Two Kubernetes connections configured — `kubernetes_local` and `kubernetes_default` (GKE). DAGs use the same operator code regardless.

---

## Pipeline: How This Replaces the Current Pub/Sub Flow

Current flow (Cloud Functions + Pub/Sub):
```
Upload → GCS → Pub/Sub → ocr_process (CF) → Pub/Sub → index_doc (CF)
```

New flow (Airflow + Spark):
```
Upload → GCS → Airflow GCS Sensor → Spark OCR Job → Spark Embed Job → KubernetesPodOperator (index)
```

| Current Component | New Component |
|-------------------|---------------|
| Pub/Sub trigger   | Airflow GCS sensor (polls every N minutes) |
| `ocr_process` Cloud Function | Spark OCR job (`jobs/ocr_job.py`) |
| `index_doc` Cloud Function | Spark embedding job (`jobs/embed_job.py`) |
| `rag_query` Cloud Function | Unchanged — stays as HTTP endpoint |
| Terraform (Cloud Functions) | Terraform updated to include GKE cluster |

---

## Local Setup: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

x-airflow-common: &airflow-common
  image: apache/airflow:2.8.0
  env_file: .env
  volumes:
    - ./dags:/opt/airflow/dags
    - ./jobs:/opt/airflow/jobs
    - ./logs:/opt/airflow/logs
    - ~/.kube:/root/.kube:ro          # share kubeconfig for GKE access
  depends_on:
    - postgres
    - redis

services:
  airflow-webserver:
    <<: *airflow-common
    command: webserver
    ports: ["8080:8080"]

  airflow-scheduler:
    <<: *airflow-common
    command: scheduler

  airflow-worker:
    <<: *airflow-common
    command: celery worker

  spark-master:
    image: bitnami/spark:3.5
    ports:
      - "7077:7077"   # Spark master
      - "8081:8081"   # Spark UI
    environment:
      - SPARK_MODE=master

  spark-worker:
    image: bitnami/spark:3.5
    environment:
      - SPARK_MODE=worker
      - SPARK_MASTER_URL=spark://spark-master:7077
      - SPARK_WORKER_MEMORY=4G
      - SPARK_WORKER_CORES=2
    depends_on: [spark-master]

  minio:
    image: minio/minio
    ports:
      - "9000:9000"   # S3 API
      - "9001:9001"   # MinIO console
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio_data:/data

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7

  qdrant:
    image: qdrant/qdrant
    ports: ["6333:6333"]
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  minio_data:
  postgres_data:
  qdrant_data:
```

---

## Airflow DAG: Document Processing Pipeline

```python
# dags/document_pipeline.py
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.providers.google.cloud.sensors.gcs import GCSObjectsWithPrefixExistenceSensor
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from datetime import datetime

with DAG(
    dag_id="document_pipeline",
    schedule_interval="*/5 * * * *",   # poll every 5 minutes for new uploads
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["lawmind", "data-engineering"],
) as dag:

    # Step 1: Watch GCS for new raw documents
    wait_for_upload = GCSObjectsWithPrefixExistenceSensor(
        task_id="wait_for_new_docs",
        bucket="{{ var.value.gcs_bucket }}",
        prefix="raw/",
        google_cloud_conn_id="google_cloud_default",
        timeout=300,
        poke_interval=60,
    )

    # Step 2: Spark OCR — extract text from PDFs at scale
    # Local: conn_id="spark_local" → spark://spark-master:7077
    # Cloud: conn_id="spark_gke"  → k8s://https://<gke-endpoint>
    ocr_job = SparkSubmitOperator(
        task_id="ocr_processing",
        application="jobs/ocr_job.py",
        conn_id="spark_local",
        application_args=[
            "--input", "gs://{{ var.value.gcs_bucket }}/raw/",
            "--output", "gs://{{ var.value.gcs_bucket }}/processed/ocr/",
        ],
        conf={
            "spark.executor.memory": "4g",
            "spark.executor.cores": "2",
            "spark.jars.packages": "com.google.cloud.bigdataoss:gcs-connector:hadoop3-2.2.17",
        },
    )

    # Step 3: Spark Embedding — chunk text and generate embeddings
    embed_job = SparkSubmitOperator(
        task_id="chunk_and_embed",
        application="jobs/embed_job.py",
        conn_id="spark_local",
        application_args=[
            "--input", "gs://{{ var.value.gcs_bucket }}/processed/ocr/",
            "--output", "gs://{{ var.value.gcs_bucket }}/processed/embeddings/",
        ],
        conf={"spark.executor.memory": "4g"},
    )

    # Step 4: Index into Qdrant — runs as a K8s pod (can target GKE)
    index_job = KubernetesPodOperator(
        task_id="index_to_qdrant",
        name="lawmind-indexer",
        image="gcr.io/{{ var.value.gcp_project }}/indexer:latest",
        namespace="default",
        kubernetes_conn_id="kubernetes_default",   # switch to "kubernetes_gke" for cloud
        env_vars={
            "QDRANT_URL": "{{ var.value.qdrant_url }}",
            "GCS_BUCKET": "{{ var.value.gcs_bucket }}",
        },
        is_delete_operator_pod=True,
        get_logs=True,
    )

    wait_for_upload >> ocr_job >> embed_job >> index_job
```

---

## Spark Jobs

### OCR Job (`jobs/ocr_job.py`)

```python
"""
Spark job: batch OCR processing of PDF documents from GCS.
Reads raw PDFs, extracts text via pytesseract, writes parquet to GCS.
"""
import argparse
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

def extract_text_from_pdf(content: bytes) -> dict:
    from pdf2image import convert_from_bytes
    import pytesseract
    images = convert_from_bytes(content)
    pages = [pytesseract.image_to_string(img) for img in images]
    return {"text": "\n\n".join(pages), "page_count": len(pages)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    spark = SparkSession.builder \
        .appName("LawmindOCR") \
        .config("spark.jars.packages",
                "com.google.cloud.bigdataoss:gcs-connector:hadoop3-2.2.17") \
        .getOrCreate()

    # Read raw PDF binary files from GCS
    df = spark.read.format("binaryFile").load(args.input + "**/*.pdf")

    # Apply OCR in parallel across executors
    schema = StructType([
        StructField("text", StringType()),
        StructField("page_count", IntegerType()),
    ])
    ocr_udf = udf(extract_text_from_pdf, schema)

    result = df.withColumn("ocr", ocr_udf("content")) \
               .select(
                   col("path"),
                   col("ocr.text").alias("text"),
                   col("ocr.page_count").alias("page_count"),
               )

    # Write results as parquet for the next Spark stage
    result.write.mode("overwrite").parquet(args.output)
    spark.stop()
```

### Embedding Job (`jobs/embed_job.py`)

```python
"""
Spark job: clause-aware chunking + OpenAI embedding generation.
Reads OCR parquet, generates embeddings, writes to GCS for indexing.
"""
import argparse
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, explode, col
from pyspark.sql.types import ArrayType, StructType, StructField, StringType, FloatType

def chunk_and_embed(text: str) -> list:
    """Split text into clauses and generate embeddings."""
    import openai, os
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", ";"],
    )
    chunks = splitter.split_text(text)

    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=chunks,
    )
    return [
        {"chunk_text": chunk, "embedding": emb.embedding}
        for chunk, emb in zip(chunks, response.data)
    ]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    spark = SparkSession.builder.appName("LawmindEmbed").getOrCreate()

    df = spark.read.parquet(args.input)

    chunk_schema = ArrayType(StructType([
        StructField("chunk_text", StringType()),
        StructField("embedding", ArrayType(FloatType())),
    ]))
    embed_udf = udf(chunk_and_embed, chunk_schema)

    result = df.withColumn("chunks", embed_udf("text")) \
               .withColumn("chunk", explode("chunks")) \
               .select(
                   col("path"),
                   col("chunk.chunk_text"),
                   col("chunk.embedding"),
               )

    result.write.mode("overwrite").parquet(args.output)
    spark.stop()
```

---

## Connecting to GKE

### One-time setup

```bash
# 1. Get GKE credentials (adds context to ~/.kube/config)
gcloud container clusters get-credentials lawmind-cluster \
    --region us-central1 \
    --project your-project-id

# 2. Create Spark namespace in GKE
kubectl create namespace spark

# 3. Give Spark service account permissions
kubectl create serviceaccount spark -n spark
kubectl create clusterrolebinding spark-role \
    --clusterrole=edit \
    --serviceaccount=spark:spark \
    --namespace=spark

# 4. In Airflow UI, add connections:
#    - Conn ID: kubernetes_default  → Type: Kubernetes  → In-cluster: false → Kubeconfig: paste GKE context
#    - Conn ID: spark_gke           → Type: Spark       → Host: k8s://https://<gke-master-endpoint>
```

### Submitting Spark jobs to GKE

```bash
# Build Spark Docker image with your dependencies
docker build -t gcr.io/your-project/spark-lawmind:latest -f Dockerfile.spark .
docker push gcr.io/your-project/spark-lawmind:latest

# Manual submit (Airflow does this automatically via SparkSubmitOperator)
spark-submit \
    --master k8s://https://$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}') \
    --deploy-mode cluster \
    --conf spark.kubernetes.container.image=gcr.io/your-project/spark-lawmind:latest \
    --conf spark.kubernetes.namespace=spark \
    --conf spark.kubernetes.authenticate.serviceAccountName=spark \
    --conf spark.executor.instances=3 \
    --conf spark.executor.memory=4g \
    jobs/ocr_job.py --input gs://your-bucket/raw/ --output gs://your-bucket/processed/ocr/
```

---

## Switching Between Local and Cloud

The only thing that changes is Airflow connection IDs and environment variables. Code is identical.

| Setting | Local | Cloud (GKE) |
|---------|-------|-------------|
| Spark conn | `spark_local` (spark://spark-master:7077) | `spark_gke` (k8s://https://...) |
| K8s conn | `kubernetes_local` | `kubernetes_default` |
| Storage | MinIO (`s3://` + endpoint override) | GCS (`gs://`) |
| Qdrant | `localhost:6333` | Cloud Qdrant or Vertex AI |

---

## Terraform: Adding GKE

Add to `infra/gcp/main.tf`:

```hcl
resource "google_container_cluster" "lawmind" {
  name     = "lawmind-cluster"
  location = var.region

  initial_node_count = 1
  remove_default_node_pool = true
}

resource "google_container_node_pool" "spark_nodes" {
  name       = "spark-pool"
  cluster    = google_container_cluster.lawmind.name
  location   = var.region

  autoscaling {
    min_node_count = 0
    max_node_count = 10
  }

  node_config {
    machine_type = "n2-standard-4"   # 4 vCPU, 16GB — good for Spark executors
    disk_size_gb = 100
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
  }
}
```

---

## Recommended Rollout Order

1. **Local first** — `docker-compose up`, write DAGs, run Spark locally against MinIO
2. **Connect real GCS** — swap MinIO endpoint for real GCS (one env var change)
3. **Connect GKE** — switch Airflow Spark conn from `spark_local` to `spark_gke`
4. **Optional** — migrate Airflow to Cloud Composer for fully managed orchestration

---

## Directory Structure for Data Engineering

```
Lawmind/
├── dags/
│   └── document_pipeline.py     # Main Airflow DAG
├── jobs/
│   ├── ocr_job.py               # Spark OCR job
│   └── embed_job.py             # Spark chunking + embedding job
├── docker-compose.yml           # Local infra (Airflow + Spark + MinIO + Qdrant)
├── Dockerfile.spark             # Spark image with Lawmind dependencies
└── infra/gcp/
    └── main.tf                  # Updated to include GKE cluster
```
