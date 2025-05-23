#!/bin/bash

# Deploy Kismet website indexing job to Google Cloud Run Jobs

# Configuration
PROJECT_ID="playgroundist"
REGION="us-central1"
JOB_NAME="kismet-site-indexer"
ARTIFACT_REGISTRY_REGION="us-central1"
REPOSITORY="cloud-run-source-deploy"
IMAGE_NAME="${ARTIFACT_REGISTRY_REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${JOB_NAME}"

echo "Building Docker image for indexing job..."

# Create a Dockerfile for the job
cat > Dockerfile.indexer <<EOF
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy NLWeb code
COPY code/ ./code/
COPY scripts/index-kismet-site.py ./scripts/index-kismet-site.py

# Install Python dependencies
RUN pip install --no-cache-dir -r code/requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the indexing script
CMD ["python", "scripts/index-kismet-site.py"]
EOF

# Create a cloudbuild.yaml file for the custom build
cat > cloudbuild-indexer.yaml <<EOF
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-f', 'Dockerfile.indexer', '-t', '${IMAGE_NAME}', '.']
images:
- '${IMAGE_NAME}'
EOF

# Build and push the Docker image using the custom cloudbuild.yaml
gcloud builds submit --config=cloudbuild-indexer.yaml --project $PROJECT_ID .

# Check if job exists and update or create accordingly
echo "Checking if Cloud Run job exists..."
if gcloud run jobs describe $JOB_NAME --region $REGION --project $PROJECT_ID &>/dev/null; then
    echo "Updating existing Cloud Run job..."
    gcloud run jobs update $JOB_NAME \
      --image $IMAGE_NAME \
      --region $REGION \
      --memory 1Gi \
      --cpu 1 \
      --max-retries 1 \
      --task-timeout 600 \
      --set-env-vars="OPENAI_API_KEY=${OPENAI_API_KEY},QDRANT_URL=${QDRANT_URL},QDRANT_API_KEY=${QDRANT_API_KEY}" \
      --project $PROJECT_ID
else
    echo "Creating new Cloud Run job..."
    gcloud run jobs create $JOB_NAME \
      --image $IMAGE_NAME \
      --region $REGION \
      --memory 1Gi \
      --cpu 1 \
      --max-retries 1 \
      --task-timeout 600 \
      --set-env-vars="OPENAI_API_KEY=${OPENAI_API_KEY},QDRANT_URL=${QDRANT_URL},QDRANT_API_KEY=${QDRANT_API_KEY}" \
      --project $PROJECT_ID
fi

# Clean up
rm Dockerfile.indexer
rm cloudbuild-indexer.yaml

echo ""
echo "Cloud Run job deployed successfully!"
echo ""
echo "To run the job manually:"
echo "  gcloud run jobs execute $JOB_NAME --region $REGION --project $PROJECT_ID"
echo ""
echo "To set up scheduled execution with Cloud Scheduler:"
echo "  1. Create a service account for Cloud Scheduler (if not exists):"
echo "     gcloud iam service-accounts create kismet-indexer-scheduler --project $PROJECT_ID"
echo ""
echo "  2. Grant necessary permissions:"
echo "     gcloud projects add-iam-policy-binding $PROJECT_ID \\"
echo "       --member=\"serviceAccount:kismet-indexer-scheduler@${PROJECT_ID}.iam.gserviceaccount.com\" \\"
echo "       --role=\"roles/run.invoker\""
echo ""
echo "  3. Create a Cloud Scheduler job (runs daily at 2 AM):"
echo "     gcloud scheduler jobs create http kismet-site-indexer-schedule \\"
echo "       --location=$REGION \\"
echo "       --schedule=\"0 2 * * *\" \\"
echo "       --uri=\"https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run\" \\"
echo "       --http-method=POST \\"
echo "       --oauth-service-account-email=\"kismet-indexer-scheduler@${PROJECT_ID}.iam.gserviceaccount.com\" \\"
echo "       --project=$PROJECT_ID" 