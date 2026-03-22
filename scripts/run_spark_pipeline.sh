#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run_spark_pipeline.sh — Lawmind local Spark document processing pipeline
#
# Runs both pipeline stages inside the running spark-master container:
#   Stage 1: OCR  — PDF → extracted text   (ocr_job.py)
#   Stage 2: Embed — text → Qdrant vectors  (embed_job.py)
#
# Prerequisites:
#   docker-compose up -d     (cluster must be running)
#   .env file with OPENAI_API_KEY set
#
# Usage:
#   bash scripts/run_spark_pipeline.sh                    # full pipeline
#   bash scripts/run_spark_pipeline.sh --ocr-only         # stage 1 only
#   bash scripts/run_spark_pipeline.sh --embed-only       # stage 2 only
#   bash scripts/run_spark_pipeline.sh --input /path/to/pdfs
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Defaults ─────────────────────────────────────────────────────────────────
INPUT_DIR="/app/storage/raw"
OCR_OUT="/app/storage/processed/ocr"
EMBED_OUT="/app/storage/processed/embeddings"
PARTITIONS=4
EXECUTOR_MEMORY="3g"
RUN_OCR=true
RUN_EMBED=true
CONTAINER="lawmind-spark-master"

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --input)         INPUT_DIR="$2";    shift 2 ;;
        --ocr-out)       OCR_OUT="$2";      shift 2 ;;
        --embed-out)     EMBED_OUT="$2";    shift 2 ;;
        --partitions)    PARTITIONS="$2";   shift 2 ;;
        --memory)        EXECUTOR_MEMORY="$2"; shift 2 ;;
        --ocr-only)      RUN_EMBED=false;   shift ;;
        --embed-only)    RUN_OCR=false;     shift ;;
        --container)     CONTAINER="$2";    shift 2 ;;
        -h|--help)
            sed -n '2,20p' "$0" | sed 's/^# \{0,2\}//'
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────
log()  { echo "[$(date '+%H:%M:%S')] $*"; }
bold() { echo -e "\033[1m$*\033[0m"; }
ok()   { echo -e "\033[32m✓ $*\033[0m"; }
err()  { echo -e "\033[31m✗ $*\033[0m"; exit 1; }

# ── Pre-flight checks ─────────────────────────────────────────────────────────
bold "=== Lawmind Spark Pipeline ==="
echo ""

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    err "Container '${CONTAINER}' is not running. Run: docker-compose up -d"
fi
ok "Spark master container is running"

# Check .env has OPENAI_API_KEY
if [[ -f .env ]]; then
    if ! grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then
        echo "⚠ Warning: OPENAI_API_KEY not found in .env (needed for Stage 2)"
    fi
else
    echo "⚠ Warning: .env file not found — OPENAI_API_KEY must be set in the environment"
fi

# ── Common spark-submit options ───────────────────────────────────────────────
SPARK_SUBMIT_OPTS=(
    "--master" "spark://spark-master:7077"
    "--conf"   "spark.executor.memory=${EXECUTOR_MEMORY}"
    "--conf"   "spark.executorEnv.PYTHONPATH=/app"
    "--conf"   "spark.executor.cores=2"
    "--conf"   "spark.sql.shuffle.partitions=${PARTITIONS}"
)

# ── Stage 1: OCR ─────────────────────────────────────────────────────────────
if [[ "$RUN_OCR" == "true" ]]; then
    bold "── Stage 1: OCR (PDF → text) ──"
    log "Input:  ${INPUT_DIR}"
    log "Output: ${OCR_OUT}"
    echo ""

    docker exec \
        -e PYTHONPATH=/app \
        "${CONTAINER}" \
        spark-submit \
        "${SPARK_SUBMIT_OPTS[@]}" \
        /app/jobs/ocr_job.py \
        --input      "${INPUT_DIR}" \
        --output     "${OCR_OUT}" \
        --partitions "${PARTITIONS}"

    ok "Stage 1 complete — OCR results in ${OCR_OUT}"
    echo ""
fi

# ── Stage 2: Embed + Index ────────────────────────────────────────────────────
if [[ "$RUN_EMBED" == "true" ]]; then
    bold "── Stage 2: Embed + Index (text → Qdrant) ──"
    log "Input:  ${OCR_OUT}"
    log "Output: ${EMBED_OUT}"
    log "Qdrant: $(docker exec ${CONTAINER} printenv QDRANT_URL 2>/dev/null || echo 'http://qdrant:6333')"
    echo ""

    docker exec \
        -e PYTHONPATH=/app \
        "${CONTAINER}" \
        spark-submit \
        "${SPARK_SUBMIT_OPTS[@]}" \
        /app/jobs/embed_job.py \
        --input      "${OCR_OUT}" \
        --output     "${EMBED_OUT}" \
        --partitions "${PARTITIONS}"

    ok "Stage 2 complete — chunks indexed in Qdrant"
    echo ""
fi

bold "=== Pipeline complete ==="
echo ""
echo "  Qdrant dashboard:    http://localhost:6333/dashboard"
echo "  Spark master UI:     http://localhost:8081"
echo "  OCR output:          storage/processed/ocr/"
echo "  Embedding output:    storage/processed/embeddings/"
