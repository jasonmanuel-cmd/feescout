from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime
import os

app = FastAPI(title="FeeScout API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("BLOCKCHAIR_API_KEY", "G___MTJ7PgczS9WHwUrUVqPVA4m4qqXf")

CHAINS = [
    "bitcoin", "bitcoin-cash", "litecoin", "bitcoin-sv", "dogecoin",
    "dash", "ripple", "groestlcoin", "stellar", "monero", "cardano",
    "zcash", "mixin", "tezos", "eos", "ethereum", "polygon",
    "arbitrum", "optimism", "base", "avalanche", "fantom",
    "bnb", "moonbeam", "cronos", "gnosis", "ecash", "solana"
]

def fetch_chain_stats(chain):
    url = f"https://api.blockchair.com/{chain}/stats?key={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json().get("data", {})
        return None
    except:
        return None

def parse_fee_data(chain, stats):
    if not stats:
        return None
    
    fee_data = {"chain": chain, "fee_usd": None, "fee_native": None, "fee_type": None}
    
    if "suggested_transaction_fee_per_byte_sat" in stats:
        sat_per_byte = stats["suggested_transaction_fee_per_byte_sat"]
        total_sat = sat_per_byte * 250
        fee_data["fee_native"] = total_sat / 100000000
        fee_data["fee_type"] = "sat/byte"
        if "market_price_usd" in stats:
            fee_data["fee_usd"] = fee_data["fee_native"] * stats["market_price_usd"]
    
    elif "suggested_transaction_fee_gwei_options" in stats:
        options = stats["suggested_transaction_fee_gwei_options"]
        normal_gwei = options.get("normal", 0)
        total_gwei = normal_gwei * 21000
        fee_data["fee_native"] = total_gwei / 1000000000
        fee_data["fee_type"] = "gwei"
        if "market_price_usd" in stats:
            fee_data["fee_usd"] = fee_data["fee_native"] * stats["market_price_usd"]
    
    elif chain == "solana" and "average_transaction_fee" in stats:
        lamports = stats["average_transaction_fee"]
        fee_data["fee_native"] = lamports / 1000000000
        fee_data["fee_type"] = "lamports"
        if "market_price_usd" in stats:
            fee_data["fee_usd"] = fee_data["fee_native"] * stats["market_price_usd"]
    
    elif "average_transaction_fee_usd" in stats:
        fee_data["fee_usd"] = stats["average_transaction_fee_usd"]
        fee_data["fee_type"] = "avg_usd"
    
    return fee_data

@app.get("/")
async def root():
    return {
        "service": "FeeScout API",
        "status": "healthy",
        "version": "1.0.0",
        "tagline": "Find the cheapest chain, every time"
    }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/gas-fees/latest")
async def get_latest_fees():
    fees = []
    for chain in CHAINS:
        stats = fetch_chain_stats(chain)
        if stats:
            fee_data = parse_fee_data(chain, stats)
            if fee_data and fee_data["fee_usd"]:
                fees.append({
                    "chain": fee_data["chain"],
                    "fee_usd": round(fee_data["fee_usd"], 6),
                    "fee_native": fee_data["fee_native"],
                    "fee_type": fee_data["fee_type"],
                    "timestamp": datetime.now().isoformat()
                })
    fees.sort(key=lambda x: x["fee_usd"])
    return {
        "success": True,
        "count": len(fees),
        "data": fees,
        "updated_at": datetime.now().isoformat()
    }

@app.get("/api/gas-fees/cheapest")
async def get_cheapest(limit: int = 5):
    fees = []
    for chain in CHAINS:
        stats = fetch_chain_stats(chain)
        if stats:
            fee_data = parse_fee_data(chain, stats)
            if fee_data and fee_data["fee_usd"]:
                fees.append({"chain": fee_data["chain"], "fee_usd": round(fee_data["fee_usd"], 6)})
    fees.sort(key=lambda x: x["fee_usd"])
    cheapest = []
    for i, fee in enumerate(fees[:limit]):
        cheapest.append({"rank": i + 1, "chain": fee["chain"], "fee_usd": fee["fee_usd"]})
    return {"success": True, "data": cheapest}

@app.get("/api/gas-fees/comparison")
async def get_comparison(amount: float = 1000):
    fees = []
    for chain in CHAINS:
        stats = fetch_chain_stats(chain)
        if stats:
            fee_data = parse_fee_data(chain, stats)
            if fee_data and fee_data["fee_usd"]:
                fees.append({"chain": fee_data["chain"], "fee_usd": fee_data["fee_usd"]})
    fees.sort(key=lambda x: x["fee_usd"])
    if len(fees) < 2:
        return {"success": False, "error": "Insufficient data"}
    cheapest = fees[0]
    comparisons = []
    for fee in fees[1:11]:
        savings = fee["fee_usd"] - cheapest["fee_usd"]
        savings_pct = (savings / fee["fee_usd"]) * 100 if fee["fee_usd"] > 0 else 0
        comparisons.append({
            "expensive_chain": fee["chain"],
            "expensive_fee": round(fee["fee_usd"], 6),
            "cheap_chain": cheapest["chain"],
            "cheap_fee": round(cheapest["fee_usd"], 6),
            "savings_usd": round(savings, 6),
            "savings_percent": round(savings_pct, 2)
        })
    return {
        "success": True,
        "transfer_amount_usd": amount,
        "cheapest_option": cheapest["chain"],
        "comparisons": comparisons
    }

handler = app
