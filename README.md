# Business Intelligence Dashboard

Sales performance intelligence platform combining Zoho CRM, Kixie call data, and revenue metrics.

## Quick Deploy to Railway

### 1. Click Deploy Button

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https%3A%2F%2Fgithub.com%2Fatlastheai%2Femployee-management)

### 2. Set Environment Variables

```
SECRET_KEY=<generate-with: openssl rand -hex 32>
ADMIN_USERNAME=carlos
ADMIN_PASSWORD=<your-secure-password>
```

### 3. Access Dashboard

Your dashboard will be live at: `https://<your-project>.up.railway.app`

## What's Inside

📊 **Intelligence Report** - Executive summary with key findings
- Top performers by efficiency (revenue per call)
- Bottom performers (termination recommendations)
- Complete performance rankings
- Gaming pattern detection
- ROI analysis

🔍 **Detailed Dashboard** - Interactive rep cards
- Click any rep for full assessment
- Call quality breakdown
- Gaming flags with explanations
- Activity tracking
- Deal performance

## Data Sources

✅ **Kixie** - 24,641 real call records
- Call durations
- Ghost call detection (≤5 sec)
- Meaningful calls (≥30 sec)
- Talk time analysis

✅ **Zoho CRM** - 43 sales reps
- Activity tracking
- Tasks & events
- Pipeline status
- Deal metrics

✅ **Revenue** - $35.6M performance data
- 125 salespeople tracked
- Total sales & commission
- Revenue rankings

## Key Findings

**Top Performer:**
- Morgan.Q: $28,598 per call (107 calls → $3.1M revenue)

**Bottom Performers:**
- robert.ca: $8 per call (4,200 calls → $35K revenue)
- jonah.go: $7 per call (3,007 calls → $22K revenue)

**Performance Gap:** 4,097x between best and worst

**Termination Savings:** ~$150K/year

## Security

🔐 Password-protected login
🔒 Session-based authentication
🔑 Environment variables for secrets
✅ No sensitive data in git

## Tech Stack

- **Backend:** Python + Flask
- **Server:** Gunicorn
- **Hosting:** Railway
- **Data:** JSON (static snapshots)

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SECRET_KEY=dev-secret-key
export ADMIN_USERNAME=admin
export ADMIN_PASSWORD=changeme

# Run app
python app.py
```

Access at: http://localhost:5000

## API Endpoints

- `GET /` - Redirect to dashboard
- `GET /login` - Login page
- `GET /dashboard` - Main intelligence report
- `GET /detailed` - Detailed interactive dashboard
- `GET /api/health` - Health check
- `GET /api/stats` - Dashboard statistics (JSON)
- `POST /api/refresh` - Refresh data (TODO)

## Project Structure

```
employee-management/
├── app.py                          # Flask application
├── requirements.txt                # Python dependencies
├── Procfile                        # Railway startup
├── railway.json                    # Railway config
├── integrations/
│   ├── login.html                 # Login page
│   ├── intelligence_report.html  # Main dashboard
│   ├── dashboard.html            # Detailed dashboard
│   ├── full_intelligence_report.json  # Data
│   ├── zoho_connector.py         # Zoho CRM
│   └── merge_kixie_data.py       # Kixie merger
└── .env                           # Local secrets (git-ignored)
```

## Future Enhancements

- [ ] Live data refresh from Zoho/Kixie APIs
- [ ] User roles (admin, manager, viewer)
- [ ] Historical trend analysis
- [ ] Export functionality (CSV, PDF)
- [ ] Scheduled auto-refresh
- [ ] Real-time notifications

## Support

Built by Atlas (atlas@attix.com)
For: Trade Alliance / ORGCOMMAND

## License

Proprietary - Internal use only
