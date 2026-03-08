#!/bin/bash

# Zoho Refresh Token Generator
# This script helps generate the authorization URL and exchange code for refresh token

CLIENT_ID="1000.6BI638G0SO63565SVTZTX9D6Y85R6V"
REDIRECT_URI="https://ai-sales-agent-production-8ad4.up.railway.app/api/zoho-oauth/callback"
SCOPE="ZohoCRM.modules.ALL,ZohoCRM.users.READ,ZohoCRM.settings.ALL"

echo "=========================================="
echo "Zoho CRM Refresh Token Generator"
echo "=========================================="
echo ""
echo "STEP 1: Visit this URL in your browser:"
echo ""
echo "https://accounts.zoho.com/oauth/v2/auth?scope=${SCOPE}&client_id=${CLIENT_ID}&response_type=code&access_type=offline&redirect_uri=${REDIRECT_URI}"
echo ""
echo "STEP 2: Authorize the application"
echo "STEP 3: Copy the 'code' parameter from the redirect URL"
echo "STEP 4: Run this command (replace YOUR_CODE with the code you copied):"
echo ""
echo "curl -X POST https://accounts.zoho.com/oauth/v2/token \\"
echo "  -d 'code=YOUR_CODE' \\"
echo "  -d 'client_id=${CLIENT_ID}' \\"
echo "  -d 'client_secret=01ffebdd60b7699356ffe673d6c94892dbd5918b09' \\"
echo "  -d 'redirect_uri=${REDIRECT_URI}' \\"
echo "  -d 'grant_type=authorization_code'"
echo ""
echo "STEP 5: Copy the 'refresh_token' from the response and update .env file"
echo "=========================================="
