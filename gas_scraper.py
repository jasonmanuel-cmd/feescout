import requests
import sqlite3
import time
from datetime import datetime
import json
import os

API_KEY = os.environ.get("BLOCKCHAIR_API_KEY", "")

# All chains supported by Blockchair
CHAINS = [
    'bitcoin', 'bitcoin-cash', 'litecoin', 'bitcoin-sv', 'dogecoin',
    'dash', 'ripple', 'groestlcoin', 'stellar', 'monero', 'cardano',
    'zcash', 'mixin', 'tezos', 'eos', 'ethereum', 'ethereum/testnet',
    'polygon', 'arbitrum', 'optimism', 'base', 'avalanche', 'fantom',
    'bnb', 'moonbeam', 'cronos', 'gnosis', 'celo', 'aurora', 
    'ecash', 'solana', 'polkadot', 'kusama'
]

def init_database():
    """Create database schema"""
    conn = sqlite3.connect('gas_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gas_fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chain TEXT NOT NULL,
            fee_usd REAL,
            fee_native REAL,
            fee_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            raw_data TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_chain_timestamp 
        ON gas_fees(chain, timestamp DESC)
    ''')
    
    conn.commit()
    conn.close()

def fetch_chain_stats(chain):
    """Fetch gas/fee stats for a single chain"""
    url = f"https://api.blockchair.com/{chain}/stats?key={API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {})
        else:
            print(f"[ERROR] {chain}: Status {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] {chain}: {e}")
        return None

def parse_fee_data(chain, stats):
    """Extract fee information based on chain type"""
    if not stats:
        return None
    
    fee_data = {
        'chain': chain,
        'fee_usd': None,
        'fee_native': None,
        'fee_type': None,
        'raw_data': json.dumps(stats)
    }
    
    # Bitcoin-like chains (satoshis per byte)
    if 'suggested_transaction_fee_per_byte_sat' in stats:
        sat_per_byte = stats['suggested_transaction_fee_per_byte_sat']
        # Standard transaction ~250 bytes
        total_sat = sat_per_byte * 250
        fee_data['fee_native'] = total_sat / 100000000  # Convert to BTC
        fee_data['fee_type'] = 'sat/byte'
        
        # Convert to USD if market price available
        if 'market_price_usd' in stats:
            fee_data['fee_usd'] = fee_data['fee_native'] * stats['market_price_usd']
    
    # Ethereum-like chains (gwei)
    elif 'suggested_transaction_fee_gwei_options' in stats:
        options = stats['suggested_transaction_fee_gwei_options']
        # Use 'normal' tier
        normal_gwei = options.get('normal', 0)
        # Standard transfer: 21000 gas units
        total_gwei = normal_gwei * 21000
        fee_data['fee_native'] = total_gwei / 1000000000  # Convert to ETH
        fee_data['fee_type'] = 'gwei'
        
        if 'market_price_usd' in stats:
            fee_data['fee_usd'] = fee_data['fee_native'] * stats['market_price_usd']
    
    # Solana (lamports)
    elif chain == 'solana' and 'average_transaction_fee' in stats:
        lamports = stats['average_transaction_fee']
        fee_data['fee_native'] = lamports / 1000000000  # Convert to SOL
        fee_data['fee_type'] = 'lamports'
        
        if 'market_price_usd' in stats:
            fee_data['fee_usd'] = fee_data['fee_native'] * stats['market_price_usd']
    
    # Cardano, Polkadot, etc. (chain-specific)
    elif 'average_transaction_fee_usd' in stats:
        fee_data['fee_usd'] = stats['average_transaction_fee_usd']
        fee_data['fee_type'] = 'avg_usd'
    
    return fee_data

def save_to_database(fee_data):
    """Save fee data to SQLite"""
    conn = sqlite3.connect('gas_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO gas_fees (chain, fee_usd, fee_native, fee_type, raw_data)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        fee_data['chain'],
        fee_data['fee_usd'],
        fee_data['fee_native'],
        fee_data['fee_type'],
        fee_data['raw_data']
    ))
    
    conn.commit()
    conn.close()

def scrape_all_chains():
    """Main scraping loop"""
    print(f"[{datetime.now()}] Starting scrape of {len(CHAINS)} chains...")
    
    for chain in CHAINS:
        stats = fetch_chain_stats(chain)
        if stats:
            fee_data = parse_fee_data(chain, stats)
            if fee_data and fee_data['fee_usd']:
                save_to_database(fee_data)
                print(f"✓ {chain}: ${fee_data['fee_usd']:.4f} USD")
            else:
                print(f"⚠ {chain}: Fee data not available")
        
        # Rate limiting: don't hammer the API
        time.sleep(0.5)
    
    print(f"[{datetime.now()}] Scrape complete!\n")

if __name__ == "__main__":
    init_database()
    
    # Run continuously
    while True:
        try:
            scrape_all_chains()
            # Wait 60 seconds before next scrape
            time.sleep(60)
        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Scraper stopped by user")
            break
        except Exception as e:
            print(f"[CRITICAL ERROR] {e}")
            time.sleep(30)