# Railway Deployment - Business Intelligence Dashboard

## Quick Deploy

### 1. Create New Railway Project

Go to: https://railway.app/new

- Click "Deploy from GitHub repo"
- Select `atlastheai/employee-management`
- Or click "Empty Project" and connect GitHub manually

### 2. Set Environment Variables

In Railway dashboard, go to **Variables** and add:

```
SECRET_KEY=<generate-random-string-here>
ADMIN_USERNAME=carlos
ADMIN_PASSWORD=<your-secure-password>

# Optional: Zoho CRM credentials (for data refresh API)
ZOHO_CLIENT_ID=<from-.env>
ZOHO_CLIENT_SECRET=<from-.env>
ZOHO_REFRESH_TOKEN=<from-.env>
ZOHO_REGION=com

# Optional: Kixie credentials
KIXIE_BUSINESS_ID=19796
KIXIE_API_KEY=<from-.env>
```

### 3. Deploy

Railway will automatically:
- Detect Python project
- Install dependencies from `requirements.txt`
- Run `gunicorn app:app`
- Assign a public URL

### 4. Access Dashboard

Your dashboard will be available at:
```
https://<your-project>.up.railway.app
```

Login with the `ADMIN_USERNAME` and `ADMIN_PASSWORD` you set.

## Project Structure

```
employee-management/
├── app.py                          # Flask application
├── requirements.txt                # Python dependencies
├── Procfile                        # Railway startup command
├── railway.json                    # Railway configuration
├── integrations/
│   ├── login.html                 # Login page
│   ├── intelligence_report.html  # Main dashboard
│   ├── dashboard.html            # Detailed dashboard
│   ├── full_intelligence_report.json  # Data source
│   ├── zoho_connector.py         # Zoho CRM integration
│   └── merge_kixie_data.py       # Kixie data merger
└── .env                           # Local secrets (NOT deployed)
```

## Routes

- `/` - Redirects to dashboard (requires login)
- `/login` - Login page
- `/logout` - Logout
- `/dashboard` - Main intelligence report
- `/detailed` - Interactive detailed dashboard
- `/api/health` - Health check endpoint
- `/api/stats` - Dashboard statistics (JSON)
- `/api/refresh` - Refresh data from Zoho/Kixie (TODO)

## Security

- ✅ Password-protected login
- ✅ Session-based authentication
- ✅ Environment variables for secrets
- ✅ `.env` file excluded from git
- ⚠️ Set strong `ADMIN_PASSWORD` in Railway
- ⚠️ Use random string for `SECRET_KEY`

## Generate Secure Keys

```bash
# SECRET_KEY (use this in Railway)
python3 -c "import secrets; print(secrets.token_hex(32))"

# Or use this one-liner:
openssl rand -hex 32
```

## Manual Deployment (Alternative)

If not using GitHub auto-deploy:

1. Install Railway CLI:
   ```bash
   npm install -g @railway/cli
   ```

2. Login:
   ```bash
   railway login
   ```

3. Initialize project:
   ```bash
   cd employee-management
   railway init
   ```

4. Deploy:
   ```bash
   railway up
   ```

5. Open in browser:
   ```bash
   railway open
   ```

## Updating the Dashboard

### Auto-Deploy (Recommended)
Push to GitHub → Railway auto-deploys

### Manual Deploy
```bash
railway up
```

## Troubleshooting

### Check Logs
```bash
railway logs
```

### Check Environment Variables
```bash
railway variables
```

### Restart Service
```bash
railway restart
```

## Future Enhancements

- [ ] Implement `/api/refresh` to pull live data from Zoho/Kixie
- [ ] Add user roles (admin, viewer)
- [ ] Schedule automatic data refreshes
- [ ] Add export functionality (CSV, PDF)
- [ ] Real-time updates via WebSockets
- [ ] Historical trend analysis

## Support

Questions? Contact: atlas@attix.com
