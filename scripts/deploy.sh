#!/bin/bash
set -e 

COMPONENT=$1
ROOT_DIR=$(pwd)

# Colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

if [ -z "$COMPONENT" ]; then
    echo -e "${RED}Usage: ./scripts/deploy.sh [backend|frontend|all]${NC}"
    exit 1
fi

echo -e "${GREEN}🚀 Initiating deployment sequence for: $COMPONENT...${NC}"

deploy_backend() {
    echo -e "${GREEN}--- [Backend Deployment] ---${NC}"
    cd "$ROOT_DIR/backend"
    
    # Check Railway CLI
    if ! command -v railway &> /dev/null; then
        echo -e "${RED}❌ Railway CLI not found. Install with: npm install -g @railway/cli${NC}"
        exit 1
    fi
    
    # Environment Check
    if [ ! -f .env ]; then
        echo -e "${RED}❌ backend/.env missing. Ensure secrets are configured.${NC}"
        exit 1
    fi

    # Quality Gate: Run Pytest
    echo "🧪 Executing test suite (Pytest + Coverage)..."
    pytest --cov=app --cov-report=term-missing
    
    # Railway Deployment
    echo "📦 Pushing to Railway..."
    # Using --detach to allow Railway's native build pipeline to handle logs
    railway up --service backend --detach
    
    echo -e "${GREEN}✅ Backend deployment triggered successfully!${NC}"
}

deploy_frontend() {
    echo -e "${GREEN}--- [Frontend Deployment] ---${NC}"
    cd "$ROOT_DIR/frontend"
    
    # Check Vercel CLI
    if ! command -v vercel &> /dev/null; then
        echo -e "${RED}❌ Vercel CLI not found. Install with: npm install -g vercel${NC}"
        exit 1
    fi
    
    # Quality Gate: Run Tests and Lint
    echo "🧪 Running unit tests and linting..."
    npm run lint
    npm test -- --watchAll=false --coverage
    
    # Production Build Verification
    echo "🏗️ Verifying production build..."
    npm run build
    
    # Vercel Deployment
    echo "📦 Deploying to Vercel Production..."
    vercel --prod
    
    echo -e "${GREEN}✅ Frontend deployed successfully!${NC}"
}

# Deployment Routing
case $COMPONENT in
    backend)
        deploy_backend
        ;;
    frontend)
        deploy_frontend
        ;;
    all)
        deploy_backend
        deploy_frontend
        ;;
    *)
        echo -e "${RED}❌ Invalid component: $COMPONENT${NC}"
        echo "Usage: ./scripts/deploy.sh [backend|frontend|all]"
        exit 1
        ;;
esac

echo -e "${GREEN}🎉 All tasks complete for $COMPONENT!${NC}"