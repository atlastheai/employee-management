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
