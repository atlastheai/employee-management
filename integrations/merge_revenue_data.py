#!/usr/bin/env python3
"""
Merge sales revenue data with Kixie + Zoho CRM data.
Creates comprehensive intelligence report.
"""

import csv
import json
import re
from collections import defaultdict

def parse_currency(value):
    """Convert currency string to float"""
    if not value or value.strip() == '':
        return 0.0
    # Remove $, commas, spaces
    cleaned = value.replace('$', '').replace(',', '').replace(' ', '').strip()
    try:
        return float(cleaned)
    except:
        return 0.0

def normalize_name(name):
    """Normalize salesperson name for matching"""
    # Remove titles, locations, parentheticals
    name = re.sub(r'\s*\([^)]*\)', '', name)  # Remove (LV), (NY), etc.
    name = name.strip().lower()
    # Remove common prefixes
    name = name.replace('sr-', '').replace('jr-', '').replace('jr ', '').replace('sr ', '')
    name = name.replace('.', '').replace(',', '').strip()
    return name

def main():
    print("Loading existing data...")
    
    # Load Zoho + Kixie merged data
    with open('integrations/zoho_report_with_kixie.json', 'r') as f:
        zoho_data = json.load(f)
    
    cv = zoho_data['cross_validation']
    ratings = zoho_data['ratings']
    
    # Create name mapping from Zoho/Kixie data
    zoho_names = {}
    for oid, rep in cv.items():
        name = rep['name'].lower().replace('.', '').replace(' ', '')
        zoho_names[name] = oid
        # Add variations
        if ' ' in rep['name']:
            parts = rep['name'].split()
            # firstname.lastname
            variant1 = f"{parts[0]}.{parts[-1]}".lower()
            zoho_names[variant1] = oid
            # firstname lastname (no dot)
            variant2 = f"{parts[0]}{parts[-1]}".lower()
            zoho_names[variant2] = oid
    
    print(f"Created {len(zoho_names)} name variations from {len(cv)} Zoho reps")
    
    # Parse revenue CSV
    print("Parsing sales revenue CSV...")
    revenue_data = {}
    
    with open('sales_revenue_data.csv', 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
        # Skip first title row ("Tatech Service")
        lines = lines[1:]
        
        reader = csv.DictReader(lines)
        for row in reader:
            try:
                rank = row.get('', '').strip()
                if not rank or not rank.isdigit():
                    continue
                
                salesperson = row.get('Salesperson', '').strip()
                if not salesperson or salesperson == 'Salesperson':
                    continue
                
                total_sales_str = row.get('Total Sales 40533', '0').strip()
                total_sales = int(total_sales_str) if total_sales_str.isdigit() else 0
                
                adj_revenue = parse_currency(row.get('Adj Revenue $26,024,185.71', '0'))
                revenue = parse_currency(row.get('Revenue $35,660,765.93', '0'))
                commission = parse_currency(row.get('Commission $2,788,712.68', '0'))
                
                # Normalize name for matching
                normalized = normalize_name(salesperson)
                
                revenue_data[normalized] = {
                    'original_name': salesperson,
                    'rank': int(rank),
                    'total_sales': total_sales,
                    'adj_revenue': adj_revenue,
                    'revenue': revenue,
                    'commission': commission
                }
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue
    
    print(f"Parsed {len(revenue_data)} salespeople from revenue CSV")
    
    # Match revenue to Zoho/Kixie reps
    print("Matching revenue data to Zoho/Kixie reps...")
    matched_count = 0
    unmatched_revenue = []
    
    for rev_name, rev_data in revenue_data.items():
        # Try direct match
        oid = zoho_names.get(rev_name)
        
        # Try variations
        if not oid:
            # Try removing dots
            no_dots = rev_name.replace('.', '')
            oid = zoho_names.get(no_dots)
        
        # Try first word match
        if not oid:
            first_word = rev_name.split()[0] if ' ' in rev_name else rev_name
            for zname, zoid in zoho_names.items():
                if first_word in zname or zname in first_word:
                    oid = zoid
                    break
        
        if oid and oid in cv:
            matched_count += 1
            cv[oid]['revenue_data'] = rev_data
        else:
            unmatched_revenue.append(rev_data['original_name'])
    
    print(f"Matched {matched_count} reps with revenue data")
    print(f"Unmatched: {len(unmatched_revenue)}")
    if unmatched_revenue[:5]:
        print(f"Sample unmatched: {unmatched_revenue[:5]}")
    
    # Calculate comprehensive metrics
    print("Calculating intelligence metrics...")
    
    for oid, rep in cv.items():
        metrics = {}
        
        # Has Kixie data?
        has_kixie = 'kixie_data' in rep
        kixie = rep.get('kixie_data', {})
        
        # Has revenue data?
        has_revenue = 'revenue_data' in rep
        rev_data = rep.get('revenue_data', {})
        
        if has_kixie and has_revenue:
            # Calculate efficiency metrics
            total_calls = kixie.get('total_calls', 0)
            revenue = rev_data.get('revenue', 0)
            
            if total_calls > 0 and revenue > 0:
                metrics['revenue_per_call'] = round(revenue / total_calls, 2)
                metrics['calls_per_1k_revenue'] = round((total_calls / revenue) * 1000, 2)
            else:
                metrics['revenue_per_call'] = 0
                metrics['calls_per_1k_revenue'] = 0
            
            # Efficiency rating (high revenue per call = efficient)
            if metrics['revenue_per_call'] > 1000:
                metrics['efficiency_rating'] = 'HIGH'
            elif metrics['revenue_per_call'] > 100:
                metrics['efficiency_rating'] = 'MEDIUM'
            else:
                metrics['efficiency_rating'] = 'LOW'
            
            # Gaming vs performance check
            ghost_pct = kixie.get('ghost_pct', 0)
            if revenue < 50000 and total_calls > 1000:
                metrics['performance_flag'] = 'HIGH_ACTIVITY_LOW_REVENUE'
            elif ghost_pct > 25 and revenue > 500000:
                metrics['performance_flag'] = 'GAMING_BUT_PRODUCING'
            elif revenue > 1000000 and ghost_pct < 10:
                metrics['performance_flag'] = 'TOP_PERFORMER'
            elif revenue > 100000 and metrics['revenue_per_call'] > 200:
                metrics['performance_flag'] = 'EFFICIENT_CLOSER'
            else:
                metrics['performance_flag'] = 'AVERAGE'
            
            rep['intelligence_metrics'] = metrics
    
    # Save comprehensive report
    output_path = 'integrations/full_intelligence_report.json'
    with open(output_path, 'w') as f:
        json.dump(zoho_data, f, indent=2)
    
    print(f"\n✅ Saved full intelligence report to {output_path}")
    print()
    
    # Summary stats
    reps_with_all_data = sum(1 for r in cv.values() if 'kixie_data' in r and 'revenue_data' in r)
    print(f"COVERAGE:")
    print(f"  • Total Zoho reps: {len(cv)}")
    print(f"  • With Kixie data: {sum(1 for r in cv.values() if 'kixie_data' in r)}")
    print(f"  • With revenue data: {sum(1 for r in cv.values() if 'revenue_data' in r)}")
    print(f"  • With ALL data: {reps_with_all_data}")
    print()
    
    # Top performers by efficiency
    efficient_reps = []
    for oid, rep in cv.items():
        if 'intelligence_metrics' in rep and rep['intelligence_metrics'].get('revenue_per_call', 0) > 0:
            efficient_reps.append((
                rep['name'],
                rep['intelligence_metrics']['revenue_per_call'],
                rep['revenue_data']['revenue'],
                rep['kixie_data']['total_calls']
            ))
    
    efficient_reps.sort(key=lambda x: x[1], reverse=True)
    
    print("TOP 10 BY EFFICIENCY (Revenue per Call):")
    for name, rev_per_call, total_rev, calls in efficient_reps[:10]:
        print(f"  {name:25s}: ${rev_per_call:>8,.0f}/call  |  ${total_rev:>12,.0f} total  |  {calls:>5,} calls")

if __name__ == '__main__':
    main()
