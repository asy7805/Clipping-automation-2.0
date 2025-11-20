#!/bin/bash
# Railway Deployment Helper Script

set -e

echo "🚀 Railway Deployment Helper"
echo "============================"
echo ""

# Check Railway CLI
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Please install it first:"
    echo "   brew install railway"
    exit 1
fi

echo "✅ Railway CLI found"
echo ""

# Check if logged in
if railway status &>/dev/null; then
    echo "✅ Already logged in to Railway"
else
    echo "🔐 Please login to Railway (will open browser)..."
    railway login
fi

echo ""

# Check if project is linked
if [ -f ".railway/project.json" ]; then
    echo "✅ Project already linked"
    PROJECT_LINKED=true
else
    echo "📝 Initializing Railway project..."
    echo "   Please follow the prompts to create or link a project"
    railway init
    PROJECT_LINKED=true
fi

echo ""

# Set environment variables from .env
if [ -f ".env" ]; then
    echo "📝 Setting environment variables from .env file..."
    echo ""
    
    # Read .env and set variables
    while IFS='=' read -r key value || [ -n "$key" ]; do
        # Skip comments and empty lines
        [[ $key =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        
        # Remove quotes from value if present
        value=$(echo "$value" | sed "s/^[\"']\(.*\)[\"']$/\1/")
        
        if [ -n "$key" ] && [ -n "$value" ]; then
            echo "  Setting $key..."
            railway variables set "$key=$value" 2>/dev/null || {
                echo "    ⚠️  Failed to set $key (may already exist or need manual setting)"
            }
        fi
    done < .env
    
    echo ""
    echo "✅ Environment variables configured"
else
    echo "⚠️  No .env file found. You'll need to set environment variables manually."
fi

echo ""
echo "🚀 Deploying to Railway..."
echo ""

railway up

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Get your URL: railway domain"
echo "   2. View logs: railway logs"
echo "   3. Test health: curl \$(railway domain)/api/v1/health"
echo "   4. View API docs: open \$(railway domain)/docs"
echo ""

