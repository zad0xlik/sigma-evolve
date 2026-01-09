# DigitalOcean Deployment Guide

This directory contains configuration files and scripts for deploying the MCP Memory Server to DigitalOcean App Platform.

## Prerequisites

### 1. Create PostgreSQL Database

The postgres MCP tool is read-only, so you'll need to create the database manually:

```bash
# Connect to PostgreSQL server
psql -h your-db-host -U postgres -d postgres

# Create the memories database
CREATE DATABASE memories;

# Verify creation
\l memories

# Exit
\q
```

Or using a single command:
```bash
PGPASSWORD='your-password' psql -h your-db-host -U postgres -c "CREATE DATABASE memories"
```

### 2. Install Required Tools

- **doctl**: DigitalOcean CLI tool
  ```bash
  # On macOS
  brew install doctl
  
  # On Linux
  sudo snap install doctl
  ```

- **Docker**: For building and pushing images
  ```bash
  # Verify installation
  docker --version
  ```

### 3. DigitalOcean API Token

1. Go to [DigitalOcean Control Panel](https://cloud.digitalocean.com/account/api/tokens)
2. Generate a new token with read/write access
3. Save the token securely

## Quick Start

1. **Configure doctl**:
   ```bash
   doctl auth init
   # Enter your API token when prompted
   ```

2. **Set environment variables**:
   ```bash
   export DO_TOKEN="your-digitalocean-api-token"
   export ENVIRONMENT="dev"  # or staging, production
   ```

3. **Deploy**:
   ```bash
   cd digitalocean
   ./deploy.sh
   ```

## Configuration Files

### app-spec.yaml

The App Platform specification defines:
- Service configuration
- Build and run commands
- Environment variables (encrypted)
- Health checks
- Resource allocation

### Parameter Files

Environment-specific configurations:
- `parameters.dev.yaml` - Development environment
- `parameters.staging.yaml` - Staging environment
- `parameters.production.yaml` - Production environment

Each file contains:
- Container registry information
- Database connection details (encrypted)
- App-specific settings

## Environment Variables

DigitalOcean App Platform uses **encrypted environment variables** instead of a separate secrets manager.

### Required Variables

Set these in the App Platform console or app spec (mark as encrypted):

```bash
DATABASE_URL=postgresql://user:password@your-db-host:5432/memories
QDRANT_URL=http://your-qdrant-instance:6333
OPENAI_API_KEY=sk-...
USER_ID=default-user
DEFAULT_APP_ID=default-app
```

### Optional Variables

```bash
LOG_LEVEL=INFO
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

## Deployment Process

### Manual Deployment via Control Panel

1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click "Create App"
3. Select "DigitalOcean Container Registry" as source
4. Choose your registry and image
5. Configure environment variables (mark sensitive ones as encrypted)
6. Review and create

### Automated Deployment via CLI

The `deploy.sh` script automates:
1. Building Docker image
2. Pushing to DigitalOcean Container Registry
3. Updating App Platform deployment

```bash
# Deploy to dev environment
ENVIRONMENT=dev ./deploy.sh

# Deploy to staging
ENVIRONMENT=staging ./deploy.sh

# Deploy to production
ENVIRONMENT=production ./deploy.sh
```

## Container Registry

### Registry Format
```
registry.digitalocean.com/your-registry-name/mcp-memory-server
```

### Tagging Strategy
- `latest` - Most recent build
- `{git-sha}` - Specific commit
- `{environment}` - Environment-specific (dev, staging, production)

## Health Checks

App Platform performs health checks on:
- **Endpoint**: `GET /health`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Healthy threshold**: 2 consecutive successes
- **Unhealthy threshold**: 3 consecutive failures

## Monitoring

### Logs
Access logs via:
1. App Platform Console
2. doctl CLI: `doctl apps logs <app-id>`
3. Log forwarding to external services

### Metrics
Monitor via App Platform dashboard:
- Request count
- Response times
- Error rates
- Resource usage (CPU, memory)

## Database Migrations

Run migrations after deployment:

```bash
# Get app ID
doctl apps list

# Run migration via console
doctl apps exec <app-id> -- alembic upgrade head

# Or access the console directly
doctl apps exec <app-id> --interactive /bin/bash
cd /app/src/openmemory
alembic upgrade head
```

## Troubleshooting

### Common Issues

**App fails to start**:
- Check environment variables are set correctly
- Verify DATABASE_URL is accessible
- Review logs: `doctl apps logs <app-id>`

**Database connection errors**:
- Verify "memories" database exists
- Check PostgreSQL server is accessible
- Confirm credentials are correct

**Container registry authentication fails**:
- Re-run: `doctl registry login`
- Verify API token has registry access

**Health check failures**:
- Ensure app is listening on port 8000
- Verify `/health` endpoint responds correctly

## Cost Considerations

### App Platform Pricing
- **Basic**: $5/month (512MB RAM, 1 vCPU)
- **Professional**: $12/month (1GB RAM, 1 vCPU)
- **Pro+**: $24/month (2GB RAM, 2 vCPU)

### Container Registry
- Free tier: 500MB storage
- Additional storage: $0.02/GB/month

### Database
- Managed PostgreSQL: Starting at $15/month
- Shared PostgreSQL (as used here): Variable cost

## Comparison with AWS

| Feature | DigitalOcean | AWS |
|---------|--------------|-----|
| **Secrets** | Encrypted env vars | Secrets Manager |
| **Deployment** | App spec YAML | CloudFormation |
| **Container Registry** | DOCR | ECR |
| **Compute** | App Platform | ECS/Fargate |
| **Complexity** | Low | Medium-High |
| **Cost** | $5-24/month | $15-50/month |

## Best Practices

1. **Use encrypted variables** for all sensitive data
2. **Tag images** with git commit SHAs for traceability
3. **Test in dev** before promoting to staging/production
4. **Monitor logs** regularly for errors
5. **Set up alerts** for critical failures
6. **Regular backups** of PostgreSQL database
7. **Use separate registries** for different environments (optional)

## Support

For issues specific to:
- **App Platform**: [DigitalOcean Support](https://www.digitalocean.com/support)
- **This project**: Check GitHub issues or create a new one
- **doctl**: [doctl documentation](https://docs.digitalocean.com/reference/doctl/)

## Next Steps

After successful deployment:
1. Run database migrations
2. Test MCP endpoints
3. Configure custom domain (optional)
4. Set up monitoring and alerts
5. Configure CI/CD pipeline
