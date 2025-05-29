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

# Build and push the Docker image using Cloud Build
echo "Building Docker image with Cloud Build..."
gcloud builds submit --tag $IMAGE_NAME --project $PROJECT_ID

# Deploy to Cloud Run (environment variables are already configured in the service)
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --region $REGION \
  --project $PROJECT_ID

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format='value(status.url)')
echo "Service deployed at: $SERVICE_URL"
echo ""
echo "Update your frontend with the new endpoint:"
echo "endpoint=\"$SERVICE_URL/ask\"" 