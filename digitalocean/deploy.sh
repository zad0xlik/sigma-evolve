#!/usr/bin/env bash
set -euo pipefail

# DigitalOcean App Platform Deployment Script for MCP Memory Server
# Usage: ENVIRONMENT=dev ./deploy.sh

# --------------------------------------------------
# Configuration
# --------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Environment (dev, staging, production)
ENVIRONMENT="${ENVIRONMENT:-dev}"

# Load parameters from yaml file
PARAM_FILE="$SCRIPT_DIR/parameters.${ENVIRONMENT}.yaml"

if [[ ! -f "$PARAM_FILE" ]]; then
  echo "❌ Error: Parameter file not found: $PARAM_FILE"
  echo "Available environments: dev, staging, production"
  exit 1
fi

echo "[$(date +'%Y-%m-%d %H:%M:%S')] 📋 Deploying to environment: $ENVIRONMENT"
echo "[$(date +'%Y-%m-%d %H:%M:%S')] 📄 Using parameters from: $PARAM_FILE"

# Parse YAML (simple parsing - assumes specific format)
REGISTRY_NAME=$(grep "name:" "$PARAM_FILE" | head -1 | awk '{print $2}' | tr -d '"')
REPO_NAME=$(grep "repository:" "$PARAM_FILE" | awk '{print $2}' | tr -d '"')
TAG=$(grep "tag:" "$PARAM_FILE" | head -1 | awk '{print $2}' | tr -d '"')
APP_NAME=$(grep "name:" "$PARAM_FILE" | tail -1 | awk '{print $2}' | tr -d '"')

# Container Registry configuration
REG="registry.digitalocean.com/${REGISTRY_NAME}"
IMAGE_NAME="${REG}/${REPO_NAME}:${TAG}"
IMAGE_LATEST="${REG}/${REPO_NAME}:latest"

# Get git commit hash for tagging
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
IMAGE_SHA="${REG}/${REPO_NAME}:${GIT_SHA}"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🏷️  Image tags:"
echo "  - ${IMAGE_NAME}"
echo "  - ${IMAGE_SHA}"
echo "  - ${IMAGE_LATEST}"

# --------------------------------------------------
# Check for required tools
# --------------------------------------------------
echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🔍 Checking for required tools..."

if ! command -v doctl &> /dev/null; then
  echo "❌ doctl is not installed. Installing..."
  if [[ "$OSTYPE" == "darwin"* ]]; then
    brew install doctl
  elif [[ -f /etc/debian_version ]]; then
    sudo snap install doctl
  else
    echo "Please install doctl manually: https://github.com/digitalocean/doctl#installing-doctl"
    exit 1
  fi
else
  echo "✅ doctl is already installed."
fi

if ! command -v docker &> /dev/null; then
  echo "❌ docker is not installed. Please install Docker first."
  exit 1
else
  echo "✅ docker is already installed."
fi

# --------------------------------------------------
# Authenticate with DigitalOcean
# --------------------------------------------------
DOCTL_CONFIG="$HOME/.config/doctl/config.yaml"

if [[ -f "$DOCTL_CONFIG" && -n "$(grep -E '^access-token:' "$DOCTL_CONFIG" 2>/dev/null || true)" ]]; then
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ doctl already configured"
else
  if [[ -n "${DO_TOKEN:-}" ]]; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🔐 Using DO_TOKEN from environment"
    doctl auth init --access-token "$DO_TOKEN"
  else
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🔐 Please authenticate with DigitalOcean"
    doctl auth init
  fi
fi

echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🚀 Authenticating with DO Container Registry..."
doctl registry login

# --------------------------------------------------
# Build Docker image
# --------------------------------------------------
echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🏗️  Building Docker image..."

cd "$PROJECT_ROOT"

docker build \
  -t "${IMAGE_NAME}" \
  -t "${IMAGE_SHA}" \
  -t "${IMAGE_LATEST}" \
  -f docker/Dockerfile \
  --build-arg ENVIRONMENT="${ENVIRONMENT}" \
  .

echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ Image built successfully"

# --------------------------------------------------
# Push to Container Registry
# --------------------------------------------------
echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🔼 Pushing image to registry..."

docker push "${IMAGE_NAME}"
docker push "${IMAGE_SHA}"
docker push "${IMAGE_LATEST}"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ Images pushed to registry"

# --------------------------------------------------
# Check if app exists
# --------------------------------------------------
echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🔍 Checking if app exists..."

APP_ID=$(doctl apps list --format ID,Spec.Name --no-header | grep "$APP_NAME" | awk '{print $1}' || echo "")

if [[ -z "$APP_ID" ]]; then
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] 📦 App does not exist. Creating new app..."
  echo ""
  echo "⚠️  MANUAL STEP REQUIRED:"
  echo "1. Go to: https://cloud.digitalocean.com/apps"
  echo "2. Click 'Create App'"
  echo "3. Choose 'DigitalOcean Container Registry'"
  echo "4. Select registry: ${REGISTRY_NAME}"
  echo "5. Select repository: ${REPO_NAME}"
  echo "6. Select tag: ${TAG}"
  echo "7. Configure environment variables from: $PARAM_FILE"
  echo "8. Name the app: ${APP_NAME}"
  echo "9. Deploy!"
  echo ""
  echo "Alternatively, use the App Platform spec file:"
  echo "  doctl apps create --spec $SCRIPT_DIR/app-spec.yaml"
  echo ""
  echo "Then re-run this script to deploy updates."
else
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ App exists with ID: $APP_ID"
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🔄 Triggering deployment..."
  
  # Update the app spec to use the new image
  # Note: This requires the app spec to be configured to use the container registry
  doctl apps create-deployment "$APP_ID"
  
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ Deployment triggered successfully"
  echo ""
  echo "Monitor deployment:"
  echo "  doctl apps get $APP_ID"
  echo "  doctl apps logs $APP_ID --type run"
  echo ""
  echo "View in console:"
  echo "  https://cloud.digitalocean.com/apps/$APP_ID"
fi

# --------------------------------------------------
# Summary
# --------------------------------------------------
echo ""
echo "======================================================================"
echo "✅ Deployment process completed for environment: $ENVIRONMENT"
echo "======================================================================"
echo ""
echo "Image pushed:"
echo "  ${IMAGE_NAME}"
echo "  ${IMAGE_SHA}"
echo ""
if [[ -n "$APP_ID" ]]; then
  echo "App ID: $APP_ID"
  echo "App Name: $APP_NAME"
  echo ""
  echo "Next steps:"
  echo "1. Monitor deployment: doctl apps get $APP_ID"
  echo "2. Check logs: doctl apps logs $APP_ID --type run"
  echo "3. Run migrations if needed:"
  echo "   doctl apps exec $APP_ID -- alembic upgrade head"
  echo "4. Test health endpoint: curl https://<your-app-url>/health"
else
  echo "Please create the app manually or using the app spec file."
fi
echo ""
echo "======================================================================"
