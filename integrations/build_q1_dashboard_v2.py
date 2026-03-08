#!/usr/bin/env python3
"""
Build Q1 2026 Performance Dashboard with proper revenue matching.
"""

import json
import csv
from datetime import datetime
from collections import defaultdict

def main():
    print("Loading data...")
    
    # Load full intelligence report (has revenue data)
    with open('integrations/full_intelligence_report.json', 'r') as f:
        intel_data = json.load(f)
    
    # Parse Kixie CSV for Q1 2026 call data
    print("Parsing Q1 2026 Kixie calls...")
    email_calls = defaultdict(lambda: {
        'total': 0,
        'ghost': 0,
        'meaningful': 0
    })
    
    with open('kixie_call_history.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                date_str = row['Date']
                dt = datetime.strptime(date_str, '%m/%d/%Y, %I:%M %p')
                
                # Only Q1 2026
                if not (dt.year == 2026 and dt.month <= 3):
                    continue
                
                email = row.get('Agent Email', '').strip().lower()
                if not email:
                    continue
                
                duration_str = row.get('Duration', '00:00')
                try:
                    parts = duration_str.split(':')
                    duration_sec = int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else 0
                except:
                    duration_sec = 0
                
                email_calls[email]['total'] += 1
                
                if duration_sec <= 5:
                    email_calls[email]['ghost'] += 1
                if duration_sec > 30:
                    email_calls[email]['meaningful'] += 1
                    
            except:
                continue
    
    print(f"Found Q1 2026 calls for {len(email_calls)} emails")
    
    # Build dashboard data from intel report
    dashboard_data = []
    
    for rep_id, rep_data in intel_data['cross_validation'].items():
        name = rep_data['name']
        
        # Skip if no Kixie data
        if 'kixie_data' not in rep_data:
            continue
        
        kixie_data = rep_data['kixie_data']
        kixie_email = kixie_data.get('email', '').lower()
        
        # Skip if no Q1 2026 calls
        if not kixie_email or kixie_email not in email_calls:
            continue
        
        q1_calls = email_calls[kixie_email]
        total_calls = q1_calls['total']
        ghost_calls = q1_calls['ghost']
        meaningful_calls = q1_calls['meaningful']
        
        ghost_pct = (ghost_calls / total_calls * 100) if total_calls > 0 else 0
        meaningful_pct = (meaningful_calls / total_calls * 100) if total_calls > 0 else 0
        
        # Get revenue from rep_data directly
        revenue = 0
        if 'revenue_data' in rep_data:
            revenue = rep_data['revenue_data'].get('revenue', 0)
        
        # Calculate revenue per call (annual revenue / Q1 calls)
        revenue_per_call = revenue / total_calls if total_calls > 0 else 0
        
        # Determine rating
        if revenue_per_call >= 2000:
            rating = 'TOP'
        elif revenue_per_call >= 500:
            rating = 'EFFICIENT'
        elif revenue_per_call >= 50:
            rating = 'AVERAGE'
        else:
            rating = 'POOR'
        
        dashboard_data.append({
            'name': name,
            'kixie_calls': total_calls,
            'ghost_pct': round(ghost_pct, 1),
            'meaningful_pct': round(meaningful_pct, 1),
            'revenue_per_call': round(revenue_per_call),
            'total_revenue': round(revenue),
            'rating': rating
        })
    
    # Sort by revenue per call
    dashboard_data.sort(key=lambda x: x['revenue_per_call'], reverse=True)
    
    print(f"\nQ1 2026 Dashboard: {len(dashboard_data)} reps")
    print(f"  With revenue: {sum(1 for r in dashboard_data if r['total_revenue'] > 0)}")
    print(f"  Without revenue: {sum(1 for r in dashboard_data if r['total_revenue'] == 0)}")
    
    # Generate HTML
    generate_html(dashboard_data)
    
    # Save JSON
    output = {
        'quarter': 'Q1 2026',
        'period': 'January - March 2026',
        'call_data_source': 'Kixie (Q1 2026 only)',
        'revenue_data_source': 'Annual (March 2025 - March 2026)',
        'note': 'Revenue figures are annual totals. Revenue-per-call uses Q1 2026 call volume.',
        'reps': dashboard_data
    }
    
    with open('integrations/q1_2026_report.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("✅ Q1 2026 dashboard generated!")
    print(f"   → integrations/q1_2026_dashboard.html")

def generate_html(data):
    """Generate Q1 2026 HTML dashboard"""
    
    html = '''<!DOCTYPE html>
<html>
<head>
    <title>Q1 2026 Performance Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            background: white;
            padding: 40px 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 30px;
            border-bottom: 3px solid #2563eb;
        }
        .header h1 {
            font-size: 36px;
            color: #1e40af;
            margin-bottom: 10px;
        }
        .header .period {
            font-size: 18px;
            color: #64748b;
            margin-bottom: 8px;
        }
        .header .note {
            font-size: 14px;
            color: #f59e0b;
            background: #fef3c7;
            padding: 10px 20px;
            border-radius: 6px;
            display: inline-block;
            margin-top: 12px;
            max-width: 800px;
        }
        .section {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .section-title {
            font-size: 24px;
            color: #1e293b;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }
        th {
            background: #f8fafc;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #475569;
            border-bottom: 2px solid #e2e8f0;
            font-size: 12px;
            text-transform: uppercase;
        }
        td {
            padding: 16px 12px;
            border-bottom: 1px solid #f1f5f9;
            color: #334155;
        }
        tr:hover { background: #f8fafc; }
        tr:nth-child(-n+3) { background: #d1fae5; }
        tr:nth-last-child(-n+3) { background: #fee2e2; }
        .badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            display: inline-block;
        }
        .badge.top { background: #065f46; color: white; }
        .badge.efficient { background: #1e40af; color: white; }
        .badge.average { background: #f59e0b; color: white; }
        .badge.poor { background: #991b1b; color: white; }
        .metric { font-weight: 600; }
        .currency { color: #059669; font-weight: 600; }
        .percentage { color: #6366f1; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Q1 2026 Performance Dashboard</h1>
            <div class="period">January - March 2026</div>
            <div class="note">
                ℹ️ Call metrics are Q1 2026 only. Revenue figures are annual (March 2025-March 2026).<br>
                Revenue-per-call calculated as: Annual Revenue ÷ Q1 2026 Calls
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📈 Complete Performance Ranking</div>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>REP</th>
                        <th>KIXIE CALLS</th>
                        <th>GHOST %</th>
                        <th>MEANINGFUL %</th>
                        <th>REVENUE PER CALL</th>
                        <th>TOTAL REVENUE</th>
                        <th>RATING</th>
                    </tr>
                </thead>
                <tbody>
'''
    
    for i, rep in enumerate(data, 1):
        rating_class = rep['rating'].lower()
        
        html += f'''
                    <tr>
                        <td>{i}</td>
                        <td><strong>{rep['name']}</strong></td>
                        <td class="metric">{rep['kixie_calls']:,}</td>
                        <td class="percentage">{rep['ghost_pct']}%</td>
                        <td class="percentage">{rep['meaningful_pct']}%</td>
                        <td class="currency">${rep['revenue_per_call']:,}</td>
                        <td class="currency">${rep['total_revenue']:,}</td>
                        <td><span class="badge {rating_class}">{rep['rating']}</span></td>
                    </tr>
'''
    
    html += '''
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
'''
    
    with open('integrations/q1_2026_dashboard.html', 'w') as f:
        f.write(html)

if __name__ == '__main__':
    main()
