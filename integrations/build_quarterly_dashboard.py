#!/usr/bin/env python3
"""
Build quarterly performance dashboard (Q1 2026).
Focuses on current quarter metrics for fair comparison.
"""

import json
import csv
from datetime import datetime
from collections import defaultdict

def main():
    print("Loading data...")
    
    # Load full intelligence report
    with open('integrations/full_intelligence_report.json', 'r') as f:
        data = json.load(f)
    
    # Parse Kixie data for Q1 2026 specifically
    print("Analyzing Q1 2026 call data...")
    q1_2026_calls = defaultdict(lambda: {
        'total_calls': 0,
        'ghost_calls': 0,
        'meaningful_calls': 0,
        'total_duration': 0
    })
    
    with open('kixie_call_history.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Parse date
                date_str = row['Date']
                dt = datetime.strptime(date_str, '%m/%d/%Y, %I:%M %p')
                
                # Only Q1 2026 (Jan-Mar 2026)
                if not (dt.year == 2026 and dt.month <= 3):
                    continue
                
                agent_email = row.get('Agent Email', '').strip().lower()
                if not agent_email:
                    continue
                
                duration_str = row.get('Duration', '00:00')
                try:
                    parts = duration_str.split(':')
                    if len(parts) == 2:
                        duration_sec = int(parts[0]) * 60 + int(parts[1])
                    else:
                        duration_sec = 0
                except:
                    duration_sec = 0
                
                q1_2026_calls[agent_email]['total_calls'] += 1
                q1_2026_calls[agent_email]['total_duration'] += duration_sec
                
                # Ghost call detection (≤5 seconds)
                if duration_sec <= 5:
                    q1_2026_calls[agent_email]['ghost_calls'] += 1
                
                # Meaningful call detection (>30 seconds)
                if duration_sec > 30:
                    q1_2026_calls[agent_email]['meaningful_calls'] += 1
                    
            except Exception as e:
                continue
    
    print(f"Processed Q1 2026 calls for {len(q1_2026_calls)} agents")
    
    # Build Q1 2026 report
    q1_report = []
    
    for rep_id, rep_data in data['cross_validation'].items():
        name = rep_data['name']
        kixie_email = rep_data.get('kixie_email', '').lower()
        
        # Skip if no Q1 2026 call data
        if kixie_email not in q1_2026_calls:
            continue
        
        q1_calls = q1_2026_calls[kixie_email]
        
        # Get revenue (note: this is full-year data from March 2025-March 2026)
        revenue_data = rep_data.get('revenue', {})
        total_revenue = revenue_data.get('revenue', 0)
        
        # Calculate Q1 2026 metrics
        total_calls = q1_calls['total_calls']
        ghost_calls = q1_calls['ghost_calls']
        meaningful_calls = q1_calls['meaningful_calls']
        
        ghost_pct = (ghost_calls / total_calls * 100) if total_calls > 0 else 0
        meaningful_pct = (meaningful_calls / total_calls * 100) if total_calls > 0 else 0
        
        # Revenue per call (using annual revenue / Q1 calls)
        # Note: This is approximate since revenue is annual
        revenue_per_call = total_revenue / total_calls if total_calls > 0 else 0
        
        q1_report.append({
            'name': name,
            'kixie_calls': total_calls,
            'ghost_pct': round(ghost_pct, 1),
            'meaningful_pct': round(meaningful_pct, 1),
            'revenue_per_call': round(revenue_per_call, 2),
            'total_revenue': round(total_revenue, 2),
            'rating': rep_data.get('rating', 'UNKNOWN')
        })
    
    # Sort by revenue per call (descending)
    q1_report.sort(key=lambda x: x['revenue_per_call'], reverse=True)
    
    print(f"\nQ1 2026 Performance Summary:")
    print(f"Reps with data: {len(q1_report)}")
    
    # Generate HTML dashboard
    generate_html(q1_report)
    
    # Save JSON
    with open('integrations/q1_2026_report.json', 'w') as f:
        json.dump({
            'quarter': 'Q1 2026',
            'period': 'January - March 2026',
            'note': 'Revenue data covers March 2025 - March 2026 (annual)',
            'reps': q1_report
        }, f, indent=2)
    
    print("✅ Q1 2026 dashboard generated!")

def generate_html(q1_report):
    """Generate HTML dashboard for Q1 2026"""
    
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
            padding: 8px 16px;
            border-radius: 6px;
            display: inline-block;
            margin-top: 10px;
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
        .badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            display: inline-block;
        }
        .badge.top { background: #d1fae5; color: #065f46; }
        .badge.efficient { background: #dbeafe; color: #1e40af; }
        .badge.average { background: #fef3c7; color: #92400e; }
        .badge.poor { background: #fee2e2; color: #991b1b; }
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
            <div class="note">⚠️ Revenue figures represent annual totals (March 2025 - March 2026)</div>
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
    
    for i, rep in enumerate(q1_report, 1):
        rating_class = {
            'TOP': 'top',
            'EFFICIENT': 'efficient',
            'AVERAGE': 'average',
            'POOR': 'poor'
        }.get(rep['rating'], 'average')
        
        html += f'''
                    <tr>
                        <td>{i}</td>
                        <td><strong>{rep['name']}</strong></td>
                        <td class="metric">{rep['kixie_calls']:,}</td>
                        <td class="percentage">{rep['ghost_pct']}%</td>
                        <td class="percentage">{rep['meaningful_pct']}%</td>
                        <td class="currency">${rep['revenue_per_call']:,.0f}</td>
                        <td class="currency">${rep['total_revenue']:,.0f}</td>
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
