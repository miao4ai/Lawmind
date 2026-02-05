#!/bin/bash
# Deploy Next.js frontend to Cloud Run

set -e

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"your-project-id"}
REGION=${GCP_REGION:-"us-central1"}
SERVICE_NAME="mamimind-frontend"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# API URL (replace with your Cloud Functions URL)
API_BASE_URL=${API_BASE_URL:-"https://your-api-url.run.app"}

echo "🚀 Deploying Mamimind Frontend to Cloud Run"
echo "   Project: ${PROJECT_ID}"
echo "   Region: ${REGION}"
echo "   API URL: ${API_BASE_URL}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first."
    exit 1
fi

# Set project
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "📦 Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com

# Build and push Docker image
echo "🔨 Building Docker image..."
gcloud builds submit \
    --tag ${IMAGE_NAME} \
    --timeout=20m \
    .

# Deploy to Cloud Run
echo "🚢 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars "NEXT_PUBLIC_API_BASE_URL=${API_BASE_URL}" \
    --timeout 60s

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --format 'value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🔗 Frontend URL: ${SERVICE_URL}"
echo "📝 API Base URL: ${API_BASE_URL}"
echo ""
echo "Next steps:"
echo "1. Update NEXT_PUBLIC_API_BASE_URL with your actual API URL"
echo "2. Configure custom domain (optional)"
echo "3. Set up CDN (optional)"
