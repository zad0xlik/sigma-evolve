#!/usr/bin/env bash
set -euo pipefail

# Unified Deployment Script for MCP Memory Server
# Supports both AWS ECS and DigitalOcean App Platform
#
# Usage:
#   PLATFORM=aws ENVIRONMENT=dev ./deploy.sh
#   PLATFORM=digitalocean ENVIRONMENT=production ./deploy.sh

# --------------------------------------------------
# Configuration
# --------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Deployment platform (aws or digitalocean)
PLATFORM="${PLATFORM:-}"

# Environment (dev, staging, production)
ENVIRONMENT="${ENVIRONMENT:-dev}"

# --------------------------------------------------
# Help message
# --------------------------------------------------
show_help() {
  cat << EOF
MCP Memory Server Deployment Script

Usage:
  PLATFORM=<platform> ENVIRONMENT=<env> ./deploy.sh

Platforms:
  aws           Deploy to AWS ECS using CloudFormation
  digitalocean  Deploy to DigitalOcean App Platform

Environments:
  dev           Development environment
  staging       Staging environment
  production    Production environment

Examples:
  # Deploy to AWS dev environment
  PLATFORM=aws ENVIRONMENT=dev ./deploy.sh

  # Deploy to DigitalOcean production
  PLATFORM=digitalocean ENVIRONMENT=production ./deploy.sh

  # Interactive mode (prompts for platform/environment)
  ./deploy.sh

Environment Variables:
  PLATFORM      Target platform (aws or digitalocean)
  ENVIRONMENT   Target environment (dev, staging, production)
  DO_TOKEN      DigitalOcean API token (for DO deployments)
  AWS_PROFILE   AWS profile to use (for AWS deployments)

Platform-Specific Scripts:
  aws/deploy.sh           AWS-specific deployment
  digitalocean/deploy.sh  DigitalOcean-specific deployment

EOF
}

# --------------------------------------------------
# Interactive prompts if not specified
# --------------------------------------------------
if [[ -z "$PLATFORM" ]]; then
  echo "Select deployment platform:"
  echo "  1) AWS ECS"
  echo "  2) DigitalOcean App Platform"
  read -p "Enter choice (1 or 2): " platform_choice
  
  case $platform_choice in
    1) PLATFORM="aws" ;;
    2) PLATFORM="digitalocean" ;;
    *)
      echo "❌ Invalid choice"
      exit 1
      ;;
  esac
fi

if [[ "$PLATFORM" != "aws" && "$PLATFORM" != "digitalocean" ]]; then
  echo "❌ Error: PLATFORM must be 'aws' or 'digitalocean'"
  echo ""
  show_help
  exit 1
fi

# --------------------------------------------------
# Validate environment
# --------------------------------------------------
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
  echo "❌ Error: ENVIRONMENT must be 'dev', 'staging', or 'production'"
  echo ""
  show_help
  exit 1
fi

# --------------------------------------------------
# Display deployment info
# --------------------------------------------------
echo "======================================================================"
echo "🚀 MCP Memory Server Deployment"
echo "======================================================================"
echo "Platform:    $PLATFORM"
echo "Environment: $ENVIRONMENT"
echo "======================================================================"
echo ""

# --------------------------------------------------
# Platform-specific deployment
# --------------------------------------------------
case $PLATFORM in
  aws)
    echo "📦 Deploying to AWS ECS..."
    if [[ ! -d "$SCRIPT_DIR/aws" ]]; then
      echo "❌ Error: AWS deployment directory not found"
      exit 1
    fi
    
    # Check for AWS CLI
    if ! command -v aws &> /dev/null; then
      echo "❌ Error: AWS CLI not installed"
      echo "Install: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
      exit 1
    fi
    
    # Delegate to AWS-specific script
    cd "$SCRIPT_DIR/aws"
    if [[ -f "deploy.sh" ]]; then
      ENVIRONMENT=$ENVIRONMENT ./deploy.sh
    else
      echo "❌ Error: aws/deploy.sh not found"
      echo "Please create AWS deployment script or use CloudFormation directly"
      exit 1
    fi
    ;;
    
  digitalocean)
    echo "📦 Deploying to DigitalOcean App Platform..."
    if [[ ! -d "$SCRIPT_DIR/digitalocean" ]]; then
      echo "❌ Error: DigitalOcean deployment directory not found"
      exit 1
    fi
    
    # Check for doctl
    if ! command -v doctl &> /dev/null; then
      echo "❌ Error: doctl not installed"
      echo "Install: brew install doctl (macOS) or https://docs.digitalocean.com/reference/doctl/how-to/install/"
      exit 1
    fi
    
    # Delegate to DigitalOcean-specific script
    cd "$SCRIPT_DIR/digitalocean"
    ENVIRONMENT=$ENVIRONMENT ./deploy.sh
    ;;
    
  *)
    echo "❌ Error: Unknown platform: $PLATFORM"
    show_help
    exit 1
    ;;
esac

# --------------------------------------------------
# Summary
# --------------------------------------------------
echo ""
echo "======================================================================"
echo "✅ Deployment completed for $PLATFORM ($ENVIRONMENT)"
echo "======================================================================"
echo ""
echo "Next steps:"
case $PLATFORM in
  aws)
    echo "1. Check CloudFormation stack status in AWS Console"
    echo "2. Monitor ECS service deployment"
    echo "3. Test health endpoint: curl https://<your-alb-url>/health"
    echo "4. Run database migrations if needed"
    ;;
  digitalocean)
    echo "1. Check app status: doctl apps list"
    echo "2. Monitor deployment logs"
    echo "3. Test health endpoint: curl https://<your-app-url>/health"
    echo "4. Run database migrations: doctl apps exec <app-id> -- alembic upgrade head"
    ;;
esac
echo ""
echo "For more information, see:"
echo "  - AWS: aws/README.md"
echo "  - DigitalOcean: digitalocean/README.md"
echo "======================================================================"
