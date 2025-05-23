#!/bin/bash

# Deploy NLWeb API to Google Cloud Run

# Configuration
PROJECT_ID="playgroundist"  # Update if needed
SERVICE_NAME="nlweb-api"
REGION="us-central1"
# Using Artifact Registry instead of Container Registry
ARTIFACT_REGISTRY_REGION="us-central1"
REPOSITORY="cloud-run-source-deploy"  # Default Cloud Run repo
IMAGE_NAME="${ARTIFACT_REGISTRY_REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}"

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY environment variable is not set"
    echo "Please set it with: export OPENAI_API_KEY=your-api-key"
    exit 1
fi

# Check if Qdrant credentials are set
if [ -z "$QDRANT_URL" ] || [ -z "$QDRANT_API_KEY" ]; then
    echo "Error: Qdrant Cloud credentials are not set"
    echo "Please set:"
    echo "  export QDRANT_URL=https://your-cluster.qdrant.io"
    echo "  export QDRANT_API_KEY=your-qdrant-api-key"
    exit 1
fi

# Build and push the Docker image using Cloud Build
echo "Building Docker image with Cloud Build..."
gcloud builds submit --tag $IMAGE_NAME --project $PROJECT_ID

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --region $REGION \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars="ENABLE_CORS=true,OPENAI_API_KEY=$OPENAI_API_KEY,QDRANT_URL=$QDRANT_URL,QDRANT_API_KEY=$QDRANT_API_KEY" \
  --project $PROJECT_ID

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format='value(status.url)')
echo "Service deployed at: $SERVICE_URL"
echo ""
echo "Update your frontend with the new endpoint:"
echo "endpoint=\"$SERVICE_URL/ask\"" 