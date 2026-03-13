#!/usr/bin/env python3
"""
Business Intelligence Dashboard - Railway Deployment
Serves the sales performance intelligence dashboard with authentication.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, send_file, jsonify, request, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash

# Initialize Flask app
app = Flask(__name__, 
            static_folder='integrations',
            template_folder='integrations')

# Secret key for sessions (set via environment variable in Railway)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Admin credentials (set via environment variables in Railway)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD_HASH = generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'changeme'))

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Redirect to dashboard"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard - Q1 2026 quarterly performance"""
    return send_file('integrations/q1_2026_dashboard.html')

@app.route('/detailed')
@login_required
def detailed_dashboard():
    """Detailed dashboard with interactive rep cards"""
    return send_file('integrations/dashboard.html')

@app.route('/data-inventory')
@login_required
def data_inventory():
    """Data inventory view"""
    return send_file('DATA_INVENTORY.html')

@app.route('/workforce')
@login_required
def workforce_dashboard():
    """Workforce analysis dashboard - 3 company portfolio"""
    return send_file('integrations/workforce_dashboard.html')

@app.route('/api/workforce-data')
@login_required
def workforce_data():
    """API endpoint for workforce analysis data"""
    data = {
        'companies': {
            'attix': {
                'name': 'Attix Inc.',
                'headcount': 89,
                'recommendation': 'Reorganize',
                'mainIssue': '17% unassigned',
                'engineering': 18,
                'sales': 23,
                'status': 'warning'
            },
            'js': {
                'name': 'JS Trading',
                'headcount': 50,
                'recommendation': 'CUT 18 (36%)',
                'mainIssue': 'Sales bloat',
                'annualPayroll': 4420000,
                'savings': 1144000,
                'engineering': 2,
                'sales': 23,
                'status': 'critical'
            },
            'vama': {
                'name': 'ATTIX VAMA',
                'headcount': 51,
                'recommendation': 'Minor trim (3-7)',
                'mainIssue': 'Well-structured',
                'technical': 28,
                'technicalPercent': 55,
                'resigning': 3,
                'status': 'good'
            }
        },
        'portfolio': {
            'totalHeadcount': 190,
            'totalPayroll': 4420000,
            'recommendedCuts': {
                'conservative': 25,
                'moderate': 33,
                'aggressive': 43
            },
            'confirmedSavings': 1144000,
            'potentialSavings': 1500000
        },
        'jsTradingCuts': {
            'tier1': {
                'name': 'HIGH PRIORITY - Cut Immediately',
                'count': 6,
                'savings': 69043,
                'employees': [
                    {'name': 'Hunter, Athena', 'dept': 'Administrative', 'salary': 19000},
                    {'name': 'Bedingfield, Victoria B', 'dept': 'Administrative', 'salary': 10523},
                    {'name': 'Bocanegra, Santiago', 'dept': 'Analysts', 'salary': 3120},
                    {'name': 'Fournier, Cameron', 'dept': 'Sales', 'salary': 13000},
                    {'name': 'Stone, Jonathan', 'dept': 'Support / Hourly', 'salary': 13000},
                    {'name': 'Cruz Gomez, Jorge', 'dept': 'Support / Hourly', 'salary': 10400}
                ]
            },
            'tier2': {
                'name': 'MEDIUM PRIORITY - Sales Bottom Performers',
                'count': 6,
                'savings': 303208,
                'employees': [
                    {'name': 'Koerick Jr., James', 'dept': 'Sales', 'salary': 43996},
                    {'name': 'Tobin, John', 'dept': 'Sales', 'salary': 44013},
                    {'name': 'Caetta, Robert', 'dept': 'Sales', 'salary': 48641},
                    {'name': 'Gozlan, Jonah', 'dept': 'Sales', 'salary': 50062},
                    {'name': 'LLC, AMC Group', 'dept': 'Sales', 'salary': 55000},
                    {'name': 'Espinoza Garcia, Jose', 'dept': 'Sales', 'salary': 61496}
                ]
            },
            'tier3': {
                'name': 'LOW PRIORITY - Contractor Review',
                'count': 6,
                'savings': 772174,
                'note': 'High-cost contractors to evaluate'
            }
        },
        'vamaCuts': {
            'natural': {
                'name': 'Natural Attrition (Already Resigning)',
                'count': 3,
                'employees': [
                    {'name': 'Chan Fan Sheng', 'role': 'Senior Finance Executive', 'dept': 'Finance'},
                    {'name': 'Muhammad Azri bin Masran', 'role': 'UI UX Designer', 'dept': 'Design'},
                    {'name': 'Song Shi Eun', 'role': 'Head of Legal', 'dept': 'Ops Team', 'critical': True}
                ]
            },
            'optional': {
                'name': 'Optional Consolidation',
                'count': 4,
                'areas': ['Finance (1)', 'Executive Assistant (1)', 'Marketing (0-1)', 'Product Management (0-1)']
            }
        }
    }
    return jsonify(data)

@app.route('/roles')
@login_required
def roles_dashboard():
    """Consolidated workforce view grouped by role category"""
    return send_file('integrations/roles_dashboard.html')

@app.route('/api/workforce-by-role')
@login_required
def workforce_by_role():
    """API endpoint for workforce data consolidated by role category across all companies"""

    # Role normalization map: maps raw titles/departments to canonical categories
    ROLE_MAP = {
        # Sales
        'sales': 'Sales',
        'sales rep': 'Sales',
        'sales representative': 'Sales',
        'account executive': 'Sales',
        'business development': 'Sales',
        # Administrative
        'administrative': 'Administrative',
        'admin': 'Administrative',
        'office manager': 'Administrative',
        'executive assistant': 'Administrative',
        # Support
        'support': 'Support',
        'support / hourly': 'Support',
        'customer support': 'Support',
        'customer service': 'Support',
        # Engineering
        'engineering': 'Engineering',
        'developer': 'Engineering',
        'software engineer': 'Engineering',
        'software developer': 'Engineering',
        'dev': 'Engineering',
        'frontend': 'Engineering',
        'backend': 'Engineering',
        'full stack': 'Engineering',
        'devops': 'Engineering',
        'qa': 'Engineering',
        # Design
        'design': 'Design',
        'ui ux designer': 'Design',
        'ui/ux': 'Design',
        'graphic designer': 'Design',
        'product designer': 'Design',
        # Finance
        'finance': 'Finance',
        'accounting': 'Finance',
        'finance executive': 'Finance',
        'senior finance executive': 'Finance',
        # Analysts
        'analysts': 'Analysts',
        'analyst': 'Analysts',
        'data analyst': 'Analysts',
        'business analyst': 'Analysts',
        # Legal
        'legal': 'Legal',
        'head of legal': 'Legal',
        # Operations
        'operations': 'Operations',
        'ops team': 'Operations',
        'ops': 'Operations',
        # Marketing
        'marketing': 'Marketing',
        # Product
        'product': 'Product',
        'product management': 'Product',
        'product manager': 'Product',
        # Management
        'management': 'Management',
        'manager': 'Management',
        'director': 'Management',
        'vp': 'Management',
        'head': 'Management',
    }

    def normalize_role(raw_role, raw_dept=None):
        """Normalize a role/department string to a canonical category."""
        if raw_role:
            key = raw_role.strip().lower()
            if key in ROLE_MAP:
                return ROLE_MAP[key]
        if raw_dept:
            key = raw_dept.strip().lower()
            if key in ROLE_MAP:
                return ROLE_MAP[key]
        return raw_role or raw_dept or 'Unassigned'

    employees = []

    # --- JS Trading employees from cut tiers ---
    js_cuts_tier1 = [
        {'name': 'Hunter, Athena', 'dept': 'Administrative', 'salary': 19000},
        {'name': 'Bedingfield, Victoria B', 'dept': 'Administrative', 'salary': 10523},
        {'name': 'Bocanegra, Santiago', 'dept': 'Analysts', 'salary': 3120},
        {'name': 'Fournier, Cameron', 'dept': 'Sales', 'salary': 13000},
        {'name': 'Stone, Jonathan', 'dept': 'Support / Hourly', 'salary': 13000},
        {'name': 'Cruz Gomez, Jorge', 'dept': 'Support / Hourly', 'salary': 10400},
    ]
    js_cuts_tier2 = [
        {'name': 'Koerick Jr., James', 'dept': 'Sales', 'salary': 43996},
        {'name': 'Tobin, John', 'dept': 'Sales', 'salary': 44013},
        {'name': 'Caetta, Robert', 'dept': 'Sales', 'salary': 48641},
        {'name': 'Gozlan, Jonah', 'dept': 'Sales', 'salary': 50062},
        {'name': 'LLC, AMC Group', 'dept': 'Sales', 'salary': 55000},
        {'name': 'Espinoza Garcia, Jose', 'dept': 'Sales', 'salary': 61496},
    ]

    for emp in js_cuts_tier1 + js_cuts_tier2:
        employees.append({
            'name': emp['name'],
            'role_category': normalize_role(None, emp['dept']),
            'role_raw': emp['dept'],
            'company': 'JS Trading',
            'salary': emp.get('salary'),
            'status': 'Flagged for Review',
            'source': 'workforce_analysis',
        })

    # --- JS Trading sales reps from Q1 report ---
    q1_path = Path('integrations/q1_2026_report.json')
    if q1_path.exists():
        with open(q1_path) as f:
            q1 = json.load(f)
        js_cut_names = {e['name'].lower() for e in js_cuts_tier1 + js_cuts_tier2}
        for rep in q1.get('reps', []):
            # Avoid duplicates with cut list (match by partial name)
            rep_lower = rep['name'].lower()
            is_dup = any(rep_lower in cn or cn in rep_lower for cn in js_cut_names)
            if not is_dup:
                employees.append({
                    'name': rep['name'],
                    'role_category': 'Sales',
                    'role_raw': 'Sales Rep',
                    'company': 'JS Trading',
                    'salary': None,
                    'status': rep.get('rating', 'Unknown'),
                    'performance': {
                        'rating': rep.get('rating'),
                        'revenue': rep.get('total_revenue'),
                        'calls': rep.get('kixie_calls'),
                    },
                    'source': 'zoho_kixie',
                })

    # --- VAMA employees ---
    vama_employees = [
        {'name': 'Chan Fan Sheng', 'role': 'Senior Finance Executive', 'dept': 'Finance', 'status': 'Resigning'},
        {'name': 'Muhammad Azri bin Masran', 'role': 'UI UX Designer', 'dept': 'Design', 'status': 'Resigning'},
        {'name': 'Song Shi Eun', 'role': 'Head of Legal', 'dept': 'Ops Team', 'status': 'Resigning (Critical)'},
    ]
    for emp in vama_employees:
        employees.append({
            'name': emp['name'],
            'role_category': normalize_role(emp.get('role'), emp.get('dept')),
            'role_raw': emp.get('role', emp.get('dept')),
            'company': 'ATTIX VAMA',
            'salary': None,
            'status': emp['status'],
            'source': 'workforce_analysis',
        })

    # --- Department-level summaries for roles without individual names ---
    # These represent known headcounts by category that we don't have individual names for
    dept_summaries = [
        {'company': 'Attix Inc.', 'role_category': 'Engineering', 'count': 18},
        {'company': 'Attix Inc.', 'role_category': 'Sales', 'count': 23},
        {'company': 'Attix Inc.', 'role_category': 'Unassigned', 'count': 15},
        {'company': 'Attix Inc.', 'role_category': 'Other', 'count': 33},
        {'company': 'ATTIX VAMA', 'role_category': 'Engineering', 'count': 28},
        {'company': 'ATTIX VAMA', 'role_category': 'Other', 'count': 20},
        {'company': 'JS Trading', 'role_category': 'Engineering', 'count': 2},
        {'company': 'JS Trading', 'role_category': 'Other', 'count': 15},
    ]

    # Build role category summary
    role_groups = {}
    for emp in employees:
        cat = emp['role_category']
        if cat not in role_groups:
            role_groups[cat] = {'named_employees': [], 'total_named': 0, 'companies': set()}
        role_groups[cat]['named_employees'].append(emp)
        role_groups[cat]['total_named'] += 1
        role_groups[cat]['companies'].add(emp['company'])

    # Add department summary counts
    for ds in dept_summaries:
        cat = ds['role_category']
        if cat not in role_groups:
            role_groups[cat] = {'named_employees': [], 'total_named': 0, 'companies': set()}
        role_groups[cat]['companies'].add(ds['company'])

    # Serialize
    result = {
        'generated_at': datetime.now().isoformat(),
        'total_known_employees': len(employees),
        'total_portfolio_headcount': 190,
        'role_categories': {},
        'department_summaries': dept_summaries,
    }

    for cat, data in sorted(role_groups.items()):
        dept_count = sum(d['count'] for d in dept_summaries if d['role_category'] == cat)
        result['role_categories'][cat] = {
            'named_count': data['total_named'],
            'estimated_total': data['total_named'] + dept_count,
            'companies': sorted(list(data['companies'])),
            'cross_company': len(data['companies']) > 1,
            'employees': data['named_employees'],
        }

    return jsonify(result)

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/refresh', methods=['POST'])
@login_required
def refresh_data():
    """
    Refresh data from Zoho CRM and Kixie
    (Placeholder - implement actual refresh logic)
    """
    try:
        # TODO: Implement actual data refresh
        # This would run the zoho_connector and merge_kixie_data scripts
        
        return jsonify({
            'status': 'success',
            'message': 'Data refresh initiated (placeholder)',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/stats')
@login_required
def stats():
    """Return dashboard statistics"""
    try:
        # Load the intelligence report data
        report_path = Path('integrations/full_intelligence_report.json')
        if report_path.exists():
            with open(report_path) as f:
                data = json.load(f)
            
            cv = data.get('cross_validation', {})
            
            # Calculate stats
            total_reps = len(cv)
            reps_with_kixie = sum(1 for r in cv.values() if 'kixie_data' in r)
            reps_with_revenue = sum(1 for r in cv.values() if 'revenue_data' in r)
            reps_with_all_data = sum(1 for r in cv.values() if 'intelligence_metrics' in r)
            
            return jsonify({
                'total_reps': total_reps,
                'reps_with_kixie': reps_with_kixie,
                'reps_with_revenue': reps_with_revenue,
                'reps_with_all_data': reps_with_all_data,
                'generated_at': data.get('generated_at', 'unknown'),
                'days_back': data.get('days_back', 90)
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'No data available'
            }), 404
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('DEBUG', 'False') == 'True')
