# Setting Up Zoho CRM API Credentials

## ✅ GitHub Access
**Status:** Invitation sent to `carlosattix` with write access to `atlastheai/employee-management`

Check your email or go to: https://github.com/atlastheai/employee-management/invitations

---

## 🔐 Where to Put the `.env` File

**Location:** `/home/node/.openclaw/workspace/employee-management/.env`

This is the **ONLY** place Claude Code will look for credentials. The file is:
- ✅ In `.gitignore` (won't be committed to GitHub)
- ✅ Only visible to you and Atlas/Claude Code on this machine
- ✅ Secure - never exposed to public repos

---

## 📝 How to Create the `.env` File

### Option 1: Directly on This Machine (Recommended)

SSH or access this machine and run:

```bash
cd /home/node/.openclaw/workspace/employee-management
nano .env
```

Then paste this content (with your real credentials):

```bash
# Zoho CRM API Credentials
ZOHO_CLIENT_ID=1000.XXXXXXXXXXXXXXXXXXXXXXXXX
ZOHO_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ZOHO_REFRESH_TOKEN=1000.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ZOHO_REGION=com
ZOHO_ORG_ID=your_org_id_here
```

Save and exit (Ctrl+X, then Y, then Enter).

### Option 2: Tell Atlas the Credentials (Secure Message)

Send me a message like:

```
Here are the Zoho credentials:
Client ID: 1000.XXXXX...
Client Secret: xxxxx...
Refresh Token: 1000.xxxxx...
Region: com
Org ID: xxxxx (or "not needed")
```

I'll create the `.env` file for you.

---

## 🔑 How to Get Zoho API Credentials

### Step 1: Go to Zoho API Console
https://api-console.zoho.com/

### Step 2: Create Server-Based Application
1. Click "Add Client"
2. Choose "Server-based Applications"
3. Fill in:
   - **Client Name:** OrgCommand (or anything)
   - **Homepage URL:** http://localhost (or your domain)
   - **Authorized Redirect URIs:** http://localhost
4. Click "Create"
5. Copy your **Client ID** and **Client Secret**

### Step 3: Generate Refresh Token
1. In the API Console, click your app
2. Go to "Generate Code" tab
3. Set **Scope:** `ZohoCRM.modules.ALL,ZohoCRM.users.READ,ZohoCRM.settings.ALL`
4. Set **Time Duration:** (doesn't matter for refresh token)
5. Click "Generate"
6. Copy the **Code** (it's temporary)
7. Run this command (replace values):

```bash
curl -X POST https://accounts.zoho.com/oauth/v2/token \
  -d "code=YOUR_CODE_HERE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "grant_type=authorization_code"
```

8. Copy the `refresh_token` from the response

### Step 4: Find Your Region
- **US:** com
- **EU:** eu
- **India:** in
- **Australia:** com.au

Check your Zoho CRM URL:
- `crm.zoho.com` → Region: `com`
- `crm.zoho.eu` → Region: `eu`
- `crm.zoho.in` → Region: `in`
- `crm.zoho.com.au` → Region: `com.au`

### Step 5: Organization ID (Optional)
Only needed if you have multiple Zoho organizations under one account. Most users can skip this or set it to `""`.

---

## ✅ Once `.env` is Set Up

1. I'll verify Claude Code can read it
2. Test the Zoho API connection
3. Begin pulling Sales KPI data per the framework

---

## 🛡️ Security Notes

- **Never commit `.env` to GitHub** (it's in `.gitignore`)
- **Refresh tokens don't expire** - treat them like passwords
- **Keep Client Secret private** - it's like a password
- **If leaked:** Regenerate credentials in Zoho API Console immediately

---

**Questions?** Ask Atlas anytime. Ready to test once `.env` is in place.
