#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run_spark_pipeline.sh — Lawmind Spark document processing pipeline
#
# Stages:
#   1. OCR      PDF → extracted text              jobs/ocr_job.py
#   1.5 Analyze OCR quality + cost estimate       jobs/analyze_job.py
#   2. Embed    text → chunks → Qdrant vectors    jobs/embed_job.py
#
# Storage modes:
#   Default (local):  reads storage/raw/,        writes storage/processed/
#   --gcs:            reads gs://<bucket>/raw/,   writes gs://<bucket>/processed/
#
# Cluster modes:
#   Default: local docker-compose  (spark://spark-master:7077)
#   --gke:   GKE cluster           (k8s://<endpoint>)
#
# Prerequisites:
#   docker-compose up -d --build     (local mode)
#   credentials/service-account.json (--gcs mode)
#   gcloud container clusters get-credentials ...  (--gke mode)
#
# Usage examples:
#   bash scripts/run_spark_pipeline.sh                     # full pipeline, local
#   bash scripts/run_spark_pipeline.sh --gcs               # full pipeline, GCS
#   bash scripts/run_spark_pipeline.sh --ocr-only          # stage 1 only
#   bash scripts/run_spark_pipeline.sh --analyze-only      # stage 1.5 only
#   bash scripts/run_spark_pipeline.sh --ocr-only --gcs    # OCR from GCS
#   bash scripts/run_spark_pipeline.sh --embed-only --gcs  # embed from GCS
#   bash scripts/run_spark_pipeline.sh --gcs --gke         # full pipeline on GKE
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
USE_GCS=false
USE_GKE=false
RUN_OCR=true
RUN_ANALYZE=true
RUN_EMBED=true
PARTITIONS=6   # 3 workers × 2 cores
EXECUTOR_MEMORY="3g"
CONTAINER="lawmind-spark-master"

# Paths (overridden when --gcs is set)
INPUT_DIR="/app/storage/raw"
OCR_OUT="/app/storage/processed/ocr"
ANALYZE_OUT="/app/storage/processed/analysis"
EMBED_OUT="/app/storage/processed/embeddings"

# GKE settings (used only with --gke)
GKE_SPARK_IMAGE=""
GKE_NAMESPACE="spark"
GKE_SA="spark"

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --gcs)               USE_GCS=true;                    shift ;;
        --gke)               USE_GKE=true;                    shift ;;
        --ocr-only)          RUN_ANALYZE=false; RUN_EMBED=false; shift ;;
        --analyze-only)      RUN_OCR=false;     RUN_EMBED=false; shift ;;
        --embed-only)        RUN_OCR=false;     RUN_ANALYZE=false; shift ;;
        --skip-analyze)      RUN_ANALYZE=false;               shift ;;
        --input)             INPUT_DIR="$2";                  shift 2 ;;
        --ocr-out)           OCR_OUT="$2";                    shift 2 ;;
        --analyze-out)       ANALYZE_OUT="$2";                shift 2 ;;
        --embed-out)         EMBED_OUT="$2";                  shift 2 ;;
        --partitions)        PARTITIONS="$2";                 shift 2 ;;
        --memory)            EXECUTOR_MEMORY="$2";            shift 2 ;;
        --gke-image)         GKE_SPARK_IMAGE="$2";            shift 2 ;;
        --gke-namespace)     GKE_NAMESPACE="$2";              shift 2 ;;
        --container)         CONTAINER="$2";                  shift 2 ;;
        -h|--help)
            sed -n '2,30p' "$0" | sed 's/^# \{0,2\}//'
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────
log()  { echo "[$(date '+%H:%M:%S')] $*"; }
bold() { echo -e "\033[1m$*\033[0m"; }
ok()   { echo -e "\033[32m✓ $*\033[0m"; }
warn() { echo -e "\033[33m⚠ $*\033[0m"; }
err()  { echo -e "\033[31m✗ $*\033[0m" >&2; exit 1; }

bold "=== Lawmind Spark Pipeline ==="
echo ""

# ── Resolve GCS paths ─────────────────────────────────────────────────────────
if [[ "$USE_GCS" == "true" ]]; then
    if [[ -z "${GCS_BUCKET:-}" ]] && [[ -f .env ]]; then
        GCS_BUCKET=$(grep -E '^GCP_STORAGE_BUCKET=' .env | cut -d= -f2 | tr -d '"' || true)
    fi
    if [[ -z "${GCS_BUCKET:-}" ]]; then
        err "GCS_BUCKET / GCP_STORAGE_BUCKET not set. Add it to .env or export GCS_BUCKET=your-bucket"
    fi
    INPUT_DIR="gs://${GCS_BUCKET}/raw"
    OCR_OUT="gs://${GCS_BUCKET}/processed/ocr"
    ANALYZE_OUT="gs://${GCS_BUCKET}/processed/analysis"
    EMBED_OUT="gs://${GCS_BUCKET}/processed/embeddings"
    log "Storage: GCS  (bucket: ${GCS_BUCKET})"
else
    log "Storage: local  (${INPUT_DIR})"
fi

# ── Pre-flight checks ─────────────────────────────────────────────────────────
if [[ "$USE_GCS" == "true" ]]; then
    if [[ ! -f "credentials/service-account.json" ]]; then
        err "credentials/service-account.json not found.\nSee credentials/README.md for setup instructions."
    fi
    ok "GCS service account key found"
fi

if [[ "$RUN_EMBED" == "true" ]]; then
    if ! grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null && [[ -z "${OPENAI_API_KEY:-}" ]]; then
        warn "OPENAI_API_KEY not found — Stage 2 (embed) will fail without it"
    else
        ok "OPENAI_API_KEY found"
    fi
fi

# ── Common spark-submit options (defined before _submit() functions) ──────────
SPARK_SUBMIT_OPTS=(
    "--conf" "spark.executor.memory=${EXECUTOR_MEMORY}"
    "--conf" "spark.executor.cores=2"
    "--conf" "spark.executorEnv.PYTHONPATH=/app"
    "--conf" "spark.sql.shuffle.partitions=${PARTITIONS}"
)

# ── Resolve cluster + define _submit() ───────────────────────────────────────
if [[ "$USE_GKE" == "true" ]]; then
    if ! command -v spark-submit &>/dev/null; then
        err "spark-submit not found on PATH.\nInstall Spark locally or use local cluster mode (drop --gke)."
    fi
    if ! command -v kubectl &>/dev/null; then
        err "kubectl not found. Install it or run in local mode (drop --gke)."
    fi
    GKE_ENDPOINT=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null)
    if [[ -z "$GKE_ENDPOINT" ]]; then
        err "No active kubectl context. Run: gcloud container clusters get-credentials <cluster> --region <region>"
    fi
    SPARK_MASTER="k8s://${GKE_ENDPOINT}"
    ok "GKE endpoint: ${GKE_ENDPOINT}"

    if [[ -z "$GKE_SPARK_IMAGE" ]]; then
        GKE_SPARK_IMAGE=$(grep -E '^GKE_SPARK_IMAGE=' .env 2>/dev/null | cut -d= -f2 | tr -d '"' || true)
    fi
    if [[ -z "$GKE_SPARK_IMAGE" ]]; then
        err "GKE_SPARK_IMAGE not set. Pass --gke-image gcr.io/your-project/spark-lawmind:latest or add to .env"
    fi

    GKE_CONF=(
        "--conf" "spark.kubernetes.container.image=${GKE_SPARK_IMAGE}"
        "--conf" "spark.kubernetes.namespace=${GKE_NAMESPACE}"
        "--conf" "spark.kubernetes.authenticate.serviceAccountName=${GKE_SA}"
        "--conf" "spark.hadoop.google.cloud.auth.type=APPLICATION_DEFAULT"
        "--conf" "spark.executor.instances=3"
        "--deploy-mode" "cluster"
    )

    _submit() {
        local job_script="$1"; shift
        spark-submit \
            --master "${SPARK_MASTER}" \
            "${GKE_CONF[@]}" \
            "${SPARK_SUBMIT_OPTS[@]}" \
            "${job_script}" "$@"
    }
    log "Cluster: GKE  (${SPARK_MASTER})"

else
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
        err "Container '${CONTAINER}' is not running.\nRun: docker-compose up -d --build"
    fi
    ok "Spark master container is running"
    SPARK_MASTER="spark://spark-master:7077"
    GKE_CONF=()

    _submit() {
        local job_script="$1"; shift
        docker exec \
            -e PYTHONPATH=/app \
            "${CONTAINER}" \
            spark-submit \
            --master "${SPARK_MASTER}" \
            "${SPARK_SUBMIT_OPTS[@]}" \
            "${job_script}" "$@"
    }
    log "Cluster: local docker-compose  (${SPARK_MASTER})"
fi

echo ""

# ── Stage 1: OCR ─────────────────────────────────────────────────────────────
if [[ "$RUN_OCR" == "true" ]]; then
    bold "── Stage 1: OCR (PDF → text) ──"
    log "Input:  ${INPUT_DIR}"
    log "Output: ${OCR_OUT}"
    echo ""

    _submit /app/jobs/ocr_job.py \
        --input      "${INPUT_DIR}" \
        --output     "${OCR_OUT}" \
        --partitions "${PARTITIONS}"

    ok "Stage 1 complete"
    echo ""
fi

# ── Stage 1.5: Analyze ───────────────────────────────────────────────────────
if [[ "$RUN_ANALYZE" == "true" ]]; then
    bold "── Stage 1.5: Analyze (OCR quality + cost estimate) ──"
    log "Input:  ${OCR_OUT}"
    log "Output: ${ANALYZE_OUT}"
    echo ""

    _submit /app/jobs/analyze_job.py \
        --input      "${OCR_OUT}" \
        --output     "${ANALYZE_OUT}" \
        --partitions "${PARTITIONS}"

    ok "Stage 1.5 complete"
    echo ""
fi

# ── Stage 2: Embed + Index ────────────────────────────────────────────────────
if [[ "$RUN_EMBED" == "true" ]]; then
    bold "── Stage 2: Embed + Index (text → Qdrant) ──"
    log "Input:  ${OCR_OUT}"
    log "Output: ${EMBED_OUT}"
    echo ""

    _submit /app/jobs/embed_job.py \
        --input      "${OCR_OUT}" \
        --output     "${EMBED_OUT}" \
        --partitions "${PARTITIONS}"

    ok "Stage 2 complete"
    echo ""
fi

# ── Summary ───────────────────────────────────────────────────────────────────
bold "=== Pipeline complete ==="
echo ""
if [[ "$USE_GKE" != "true" ]]; then
    echo "  Spark UI:         http://localhost:8081"
    echo "  Qdrant:           http://localhost:6333/dashboard"
fi
if [[ "$USE_GCS" == "true" ]]; then
    echo "  OCR output:       gs://${GCS_BUCKET}/processed/ocr/"
    echo "  Analysis output:  gs://${GCS_BUCKET}/processed/analysis/"
    echo "  Embed output:     gs://${GCS_BUCKET}/processed/embeddings/"
else
    echo "  OCR output:       storage/processed/ocr/"
    echo "  Analysis output:  storage/processed/analysis/"
    echo "  Embed output:     storage/processed/embeddings/"
fi
