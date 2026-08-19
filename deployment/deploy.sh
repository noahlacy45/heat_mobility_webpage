#!/bin/bash

# HEAT Mobility Assessment - Cloud Run Deployment Script
# Deploys the backend API to Google Cloud Run

set -e

# Configuration - UPDATE THESE VALUES
PROJECT_ID="norse-coral-441421-r9"
REGION="us-east4"
SERVICE_NAME="heat-mobility-api"
DB_CONNECTION_NAME="norse-coral-441421-r9:us-east4:replay-baseball-player-dev"
GCS_BUCKET_NAME="mobility_program_output"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting HEAT Mobility API Deployment${NC}"
echo "========================================"

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo -e "${GREEN}Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID

echo -e "${GREEN}Enabling required APIs...${NC}"
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable sqladmin.googleapis.com

echo -e "${GREEN}Building and deploying to Cloud Run...${NC}"
cd ../backend

gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --max-instances 10 \
  --set-env-vars "DB_PORT=3306,GCS_BUCKET_NAME=${GCS_BUCKET_NAME},GCP_PROJECT_ID=${PROJECT_ID}" \
  --add-cloudsql-instances $DB_CONNECTION_NAME

SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Successful!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "API URL: ${YELLOW}$SERVICE_URL${NC}"
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "1. Update frontend/index.html with the API URL:"
echo "   const API_URL = '$SERVICE_URL/api';"
echo ""
echo "2. Deploy your frontend to Firebase Hosting or a GCS static bucket"
echo "   (same as the wellness questionnaire frontend)"
echo ""
echo "3. Grant the Cloud Run service account storage access:"
echo "   gsutil iam ch serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com:objectCreator gs://${GCS_BUCKET_NAME}"
echo ""
echo "4. Test the health endpoint:"
echo "   curl \$SERVICE_URL/health"
echo ""
