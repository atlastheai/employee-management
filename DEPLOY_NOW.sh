#!/bin/bash
# One-click Railway deployment script

echo "🚀 Business Intelligence Dashboard - Railway Deployment"
echo ""
echo "This will deploy your dashboard to Railway."
echo ""

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "📦 Installing Railway CLI..."
    npm install -g @railway/cli
fi

# Login with token
echo "🔐 Authenticating with Railway..."
export RAILWAY_TOKEN="b83fa806-40bc-4554-b372-f0c298688a67"

# Initialize project
echo "🏗️  Creating Railway project..."
railway init --name business-intelligence-dashboard

# Link to GitHub repo
echo "🔗 Linking GitHub repository..."
railway link

# Set environment variables
echo "⚙️  Setting environment variables..."
railway variables set SECRET_KEY=fb5ba5e58b15a5c82d2ffd77c7fbaa58268e5791e2b3dec2d6d01cbe2b85aaaf
railway variables set ADMIN_USERNAME=carlos
echo "Enter admin password:"
read -s ADMIN_PASSWORD
railway variables set ADMIN_PASSWORD=$ADMIN_PASSWORD

# Deploy
echo "🚀 Deploying to Railway..."
railway up

# Get URL
echo ""
echo "✅ Deployment complete!"
echo ""
railway status
echo ""
echo "🌐 Your dashboard is deploying..."
echo "Run 'railway open' to view it in browser"
echo ""
