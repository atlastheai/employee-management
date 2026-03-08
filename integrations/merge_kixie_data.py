#!/usr/bin/env python3
"""
Merge Kixie call data with Zoho CRM report.
Updates zoho_report.json with real Kixie call metrics.
"""

import csv
import json
from collections import defaultdict
from datetime import datetime

def parse_duration(duration_str):
    """Convert MM:SS to seconds"""
    if not duration_str or duration_str == '':
        return 0
    try:
        parts = duration_str.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0
    except:
        return 0

def main():
    print("Loading Zoho report...")
    with open('integrations/zoho_report.json', 'r') as f:
        zoho_data = json.load(f)
    
    cv = zoho_data['cross_validation']
    
    # Create email to Zoho rep ID mapping
    email_to_oid = {}
    for oid, rep in cv.items():
        name = rep['name']
        # Try multiple email patterns
        patterns = [
            name.replace('.', '').replace(' ', '').lower(),
            name.replace(' ', '.').lower(),
            name.split()[0].lower() + '.' + name.split()[-1].lower() if ' ' in name else name.lower()
        ]
        for pattern in patterns:
            email = f"{pattern}@tradealliance.io"
            email_to_oid[email] = oid
    
    print(f"Created {len(email_to_oid)} email mappings for {len(cv)} reps")
    
    # Parse Kixie CSV
    print("Parsing Kixie call history CSV...")
    call_stats = defaultdict(lambda: {
        'total_calls': 0,
        'answered_calls': 0,
        'missed_calls': 0,
        'total_duration_sec': 0,
        'ghost_calls': 0,  # <=5 seconds
        'short_calls': 0,  # 6-29 seconds
        'meaningful_calls': 0,  # >=30 seconds
        'outgoing_calls': 0,
        'incoming_calls': 0,
        'kixie_email': None
    })
    
    matched_count = 0
    unmatched_emails = set()
    
    with open('kixie_call_history.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get('Agent Email', '').strip()
            if not email:
                continue
            
            # Try to match to Zoho rep
            oid = email_to_oid.get(email)
            if oid:
                matched_count += 1
                duration_sec = parse_duration(row.get('Duration', ''))
                call_type = row.get('Type', '')
                status = row.get('Status', '')
                
                stats = call_stats[oid]
                stats['kixie_email'] = email
                stats['total_calls'] += 1
                stats['total_duration_sec'] += duration_sec
                
                if status == 'Answered':
                    stats['answered_calls'] += 1
                elif status == 'Missed':
                    stats['missed_calls'] += 1
                
                if call_type == 'Outgoing':
                    stats['outgoing_calls'] += 1
                elif call_type == 'Incoming':
                    stats['incoming_calls'] += 1
                
                # Classify by duration
                if duration_sec <= 5:
                    stats['ghost_calls'] += 1
                elif duration_sec <= 29:
                    stats['short_calls'] += 1
                else:
                    stats['meaningful_calls'] += 1
            else:
                unmatched_emails.add(email)
    
    print(f"Matched {matched_count} calls to Zoho reps")
    print(f"Unmatched emails: {len(unmatched_emails)}")
    if unmatched_emails:
        print("Sample unmatched:", list(unmatched_emails)[:5])
    
    # Merge with Zoho data
    print("Merging Kixie data with Zoho report...")
    for oid, stats in call_stats.items():
        if oid in cv:
            # Add Kixie call quality metrics
            cv[oid]['kixie_data'] = {
                'total_calls': stats['total_calls'],
                'answered_calls': stats['answered_calls'],
                'missed_calls': stats['missed_calls'],
                'outgoing_calls': stats['outgoing_calls'],
                'incoming_calls': stats['incoming_calls'],
                'total_duration_sec': stats['total_duration_sec'],
                'total_duration_min': round(stats['total_duration_sec'] / 60, 1),
                'ghost_calls': stats['ghost_calls'],
                'short_calls': stats['short_calls'],
                'meaningful_calls': stats['meaningful_calls'],
                'ghost_pct': round(100 * stats['ghost_calls'] / stats['total_calls'], 1) if stats['total_calls'] > 0 else 0,
                'meaningful_pct': round(100 * stats['meaningful_calls'] / stats['total_calls'], 1) if stats['total_calls'] > 0 else 0,
                'avg_call_duration_sec': round(stats['total_duration_sec'] / stats['total_calls'], 1) if stats['total_calls'] > 0 else 0,
                'email': stats['kixie_email']
            }
    
    # Save updated report
    output_path = 'integrations/zoho_report_with_kixie.json'
    with open(output_path, 'w') as f:
        json.dump(zoho_data, f, indent=2)
    
    print(f"✅ Saved merged report to {output_path}")
    print()
    print("Summary:")
    print(f"  • Total Zoho reps: {len(cv)}")
    print(f"  • Reps with Kixie data: {len(call_stats)}")
    print(f"  • Total calls processed: {matched_count}")
    print()
    
    # Show top callers
    sorted_reps = sorted(call_stats.items(), key=lambda x: x[1]['total_calls'], reverse=True)
    print("Top 5 callers:")
    for oid, stats in sorted_reps[:5]:
        rep_name = cv[oid]['name']
        kixie = cv[oid]['kixie_data']
        print(f"  {rep_name:20s}: {kixie['total_calls']:4d} calls, {kixie['meaningful_pct']:5.1f}% meaningful, {kixie['ghost_pct']:5.1f}% ghost")

if __name__ == '__main__':
    main()
