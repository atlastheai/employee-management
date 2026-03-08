#!/bin/bash

# Zoho CRM Discovery Script
# Analyzes available modules, fields, and data quality

set -e

# Load credentials
source /home/node/.openclaw/workspace/employee-management/.env

# Get access token
echo "Getting access token..."
TOKEN_RESPONSE=$(curl -s -X POST 'https://accounts.zoho.com/oauth/v2/token' \
  -d "refresh_token=$ZOHO_REFRESH_TOKEN" \
  -d "client_id=$ZOHO_CLIENT_ID" \
  -d "client_secret=$ZOHO_CLIENT_SECRET" \
  -d "grant_type=refresh_token")

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
  echo "ERROR: Failed to get access token"
  echo "$TOKEN_RESPONSE"
  exit 1
fi

echo "✅ Access token obtained"

# Output file
OUTPUT_FILE="/home/node/.openclaw/workspace/employee-management/crm_analysis/ZOHO_CRM_ANALYSIS.md"

# Start report
cat > "$OUTPUT_FILE" << 'EOF'
# Zoho CRM Discovery & Analysis Report

**Generated:** $(date -u)
**Purpose:** Understand available data for anti-gaming sales metrics

---

## 1. Available Modules

EOF

# Get modules
echo "Discovering modules..."
curl -s -X GET 'https://www.zohoapis.com/crm/v2/settings/modules' \
  -H "Authorization: Zoho-oauthtoken $ACCESS_TOKEN" >> "$OUTPUT_FILE.json"

echo "" >> "$OUTPUT_FILE"
echo "### Modules Found:" >> "$OUTPUT_FILE"
echo '```json' >> "$OUTPUT_FILE"
cat "$OUTPUT_FILE.json" | grep -o '"api_name":"[^"]*"' | head -20 >> "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Get Deals module fields
echo "Analyzing Deals module..."
cat >> "$OUTPUT_FILE" << 'EOF'

## 2. Deals Module Analysis

EOF

curl -s -X GET 'https://www.zohoapis.com/crm/v2/settings/fields?module=Deals' \
  -H "Authorization: Zoho-oauthtoken $ACCESS_TOKEN" > "$OUTPUT_FILE.deals.json"

echo '### Available Fields:' >> "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"
grep -o '"api_name":"[^"]*"' "$OUTPUT_FILE.deals.json" | head -30 >> "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Get Activities
echo "Analyzing Activities..."
cat >> "$OUTPUT_FILE" << 'EOF'

## 3. Activities & Tasks

EOF

curl -s -X GET 'https://www.zohoapis.com/crm/v2/Activities' \
  -H "Authorization: Zoho-oauthtoken $ACCESS_TOKEN" > "$OUTPUT_FILE.activities.json"

echo '### Recent Activities (Sample):' >> "$OUTPUT_FILE"
echo '```json' >> "$OUTPUT_FILE"
head -50 "$OUTPUT_FILE.activities.json" >> "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Get Calls
echo "Analyzing Calls..."
cat >> "$OUTPUT_FILE" << 'EOF'

## 4. Call Logs

EOF

curl -s -X GET 'https://www.zohoapis.com/crm/v2/Calls?per_page=50' \
  -H "Authorization: Zoho-oauthtoken $ACCESS_TOKEN" > "$OUTPUT_FILE.calls.json"

echo '### Recent Calls (Sample):' >> "$OUTPUT_FILE"
echo '```json' >> "$OUTPUT_FILE"
head -50 "$OUTPUT_FILE.calls.json" >> "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Get sample deals
echo "Sampling recent deals..."
cat >> "$OUTPUT_FILE" << 'EOF'

## 5. Recent Deals (Data Quality Check)

EOF

curl -s -X GET 'https://www.zohoapis.com/crm/v2/Deals?per_page=20' \
  -H "Authorization: Zoho-oauthtoken $ACCESS_TOKEN" > "$OUTPUT_FILE.deals_sample.json"

echo '### Sample Deal Data:' >> "$OUTPUT_FILE"
echo '```json' >> "$OUTPUT_FILE"
head -100 "$OUTPUT_FILE.deals_sample.json" >> "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Summary
cat >> "$OUTPUT_FILE" << 'EOF'

## 6. Recommendations

**Based on this analysis, the following metrics are recommended:**

### Tier 1: High-Quality Metrics (Hard to Game)
- **Win Rate** - Actual closed deals vs. total opportunities
- **Revenue Attainment** - Closed revenue vs. quota
- **Average Deal Size** - Deal quality indicator
- **Discount Rate** - Margin preservation

### Tier 2: Activity Quality Metrics (Cross-Validated)
- **Call → Meeting Conversion** - Requires prospect participation
- **Meeting → Proposal Conversion** - Indicates real progress
- **Email Reply Rate** - Requires engagement
- **Response Time to Inbound Leads** - Responsiveness quality

### Tier 3: Activity Volume (With Grain of Salt)
- **Call Volume** - Track but validate against conversions
- **Email Volume** - Track but validate against replies
- **Meeting Volume** - Track but validate against attendance

### Anti-Gaming Strategy
**Cross-validate metrics:**
- High activity + Low conversions = Gaming
- High talk time + Low meetings = VM rambling
- High emails + Low replies = Spamming

**Next Steps:**
1. Identify which fields are consistently populated
2. Design scoring formulas based on available data
3. Build connector to pull these metrics daily

EOF

echo "✅ Analysis complete: $OUTPUT_FILE"
echo ""
echo "Cleaning up temporary JSON files..."
rm -f "$OUTPUT_FILE".*.json

echo ""
echo "📊 Report generated at: $OUTPUT_FILE"
