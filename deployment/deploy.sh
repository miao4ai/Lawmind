#!/bin/bash
# Deploy all Cloud Functions and infrastructure

set -e

PROJECT_ID=${GCP_PROJECT_ID:-"your-project-id"}
REGION=${GCP_REGION:-"us-central1"}

echo "🚀 Deploying Mamimind to GCP Project: $PROJECT_ID"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first."
    exit 1
fi

# Set project
gcloud config set project $PROJECT_ID

# Deploy Cloud Functions
echo "📦 Deploying Cloud Functions..."

# 1. Upload Doc
echo "  → Deploying upload_doc..."
gcloud functions deploy upload-doc \
    --gen2 \
    --runtime python311 \
    --region $REGION \
    --source services/upload_doc \
    --entry-point handle_upload \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars GCP_PROJECT_ID=$PROJECT_ID \
    --memory 256MB \
    --timeout 60s

# 2. OCR Process (Pub/Sub triggered)
echo "  → Deploying ocr_process..."
gcloud functions deploy ocr-process \
    --gen2 \
    --runtime python311 \
    --region $REGION \
    --source services/ocr_process \
    --entry-point handle_ocr \
    --trigger-topic ocr-process \
    --set-env-vars GCP_PROJECT_ID=$PROJECT_ID \
    --memory 1GB \
    --timeout 540s

# 3. Index Doc (Pub/Sub triggered)
echo "  → Deploying index_doc..."
gcloud functions deploy index-doc \
    --gen2 \
    --runtime python311 \
    --region $REGION \
    --source services/index_doc \
    --entry-point handle_index \
    --trigger-topic index-doc \
    --set-env-vars GCP_PROJECT_ID=$PROJECT_ID \
    --memory 1GB \
    --timeout 540s

# 4. RAG Query
echo "  → Deploying rag_query..."
gcloud functions deploy rag-query \
    --gen2 \
    --runtime python311 \
    --region $REGION \
    --source services/rag_query \
    --entry-point handle_query \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars GCP_PROJECT_ID=$PROJECT_ID \
    --memory 512MB \
    --timeout 60s \
    --min-instances 1  # Keep warm for low latency

# 5. Doc Status
echo "  → Deploying doc_status..."
gcloud functions deploy doc-status \
    --gen2 \
    --runtime python311 \
    --region $REGION \
    --source services/doc_status \
    --entry-point handle_status \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars GCP_PROJECT_ID=$PROJECT_ID \
    --memory 256MB \
    --timeout 30s

echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "  1. Set up environment variables in Secret Manager"
echo "  2. Deploy frontend to Cloud Run or Vercel"
echo "  3. Configure domain and SSL"
echo "  4. Set up monitoring and alerts"
echo ""
echo "🔗 Function URLs:"
gcloud functions describe upload-doc --region $REGION --format="value(serviceConfig.uri)"
gcloud functions describe rag-query --region $REGION --format="value(serviceConfig.uri)"
gcloud functions describe doc-status --region $REGION --format="value(serviceConfig.uri)"
