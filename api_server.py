from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)  # Allow frontend to access API

def get_db_connection():
    conn = sqlite3.connect('gas_data.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/gas-fees/latest', methods=['GET'])
def get_latest_fees():
    """Get the most recent gas fee for each chain"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get latest entry for each chain
    cursor.execute('''
        SELECT g1.*
        FROM gas_fees g1
        INNER JOIN (
            SELECT chain, MAX(timestamp) as max_time
            FROM gas_fees
            GROUP BY chain
        ) g2
        ON g1.chain = g2.chain AND g1.timestamp = g2.max_time
        WHERE g1.fee_usd IS NOT NULL
        ORDER BY g1.fee_usd ASC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    fees = []
    for row in rows:
        fees.append({
            'chain': row['chain'],
            'fee_usd': round(row['fee_usd'], 6),
            'fee_native': row['fee_native'],
            'fee_type': row['fee_type'],
            'timestamp': row['timestamp']
        })
    
    return jsonify({
        'success': True,
        'count': len(fees),
        'data': fees,
        'updated_at': datetime.now().isoformat()
    })

@app.route('/api/gas-fees/cheapest', methods=['GET'])
def get_cheapest():
    """Get top 5 cheapest chains (for free tier)"""
    limit = request.args.get('limit', 5, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT g1.*
        FROM gas_fees g1
        INNER JOIN (
            SELECT chain, MAX(timestamp) as max_time
            FROM gas_fees
            GROUP BY chain
        ) g2
        ON g1.chain = g2.chain AND g1.timestamp = g2.max_time
        WHERE g1.fee_usd IS NOT NULL
        ORDER BY g1.fee_usd ASC
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    cheapest = []
    for row in rows:
        cheapest.append({
            'rank': len(cheapest) + 1,
            'chain': row['chain'],
            'fee_usd': round(row['fee_usd'], 6),
            'savings_vs_eth': None  # Calculate relative to Ethereum
        })
    
    return jsonify({
        'success': True,
        'data': cheapest
    })

@app.route('/api/gas-fees/comparison', methods=['GET'])
def get_comparison():
    """Calculate savings between chains"""
    amount = request.args.get('amount', 1000, type=float)  # Default $1000 transfer
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT g1.chain, g1.fee_usd
        FROM gas_fees g1
        INNER JOIN (
            SELECT chain, MAX(timestamp) as max_time
            FROM gas_fees
            GROUP BY chain
        ) g2
        ON g1.chain = g2.chain AND g1.timestamp = g2.max_time
        WHERE g1.fee_usd IS NOT NULL
        ORDER BY g1.fee_usd ASC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) < 2:
        return jsonify({'success': False, 'error': 'Insufficient data'})
    
    cheapest = rows[0]
    comparisons = []
    
    for row in rows[1:]:
        savings = row['fee_usd'] - cheapest['fee_usd']
        savings_pct = (savings / row['fee_usd']) * 100 if row['fee_usd'] > 0 else 0
        
        comparisons.append({
            'expensive_chain': row['chain'],
            'expensive_fee': round(row['fee_usd'], 6),
            'cheap_chain': cheapest['chain'],
            'cheap_fee': round(cheapest['fee_usd'], 6),
            'savings_usd': round(savings, 6),
            'savings_percent': round(savings_pct, 2)
        })
    
    return jsonify({
        'success': True,
        'transfer_amount_usd': amount,
        'cheapest_option': cheapest['chain'],
        'comparisons': comparisons[:10]  # Top 10 savings opportunities
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'gas-arbitrage-api'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)