from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import requests
from datetime import datetime, timedelta
import os
import json

app = FastAPI(title="FeeScout API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("BLOCKCHAIR_API_KEY")
if not API_KEY:
    raise RuntimeError("BLOCKCHAIR_API_KEY environment variable is required")

CHAINS = [
    "bitcoin", "bitcoin-cash", "litecoin", "bitcoin-sv", "dogecoin",
    "dash", "ripple", "groestlcoin", "stellar", "monero", "cardano",
    "zcash", "mixin", "tezos", "eos", "ethereum", "polygon",
    "arbitrum", "optimism", "base", "avalanche", "fantom",
    "bnb", "moonbeam", "cronos", "gnosis", "ecash", "solana"
]

# In-memory cache
_cache = {
    "data": None,
    "timestamp": None,
    "ttl_seconds": 60
}

def get_cached_fees():
    """Return cached fee data if fresh, else fetch from Blockchair."""
    now = datetime.now()
    if _cache["data"] and _cache["timestamp"]:
        age = (now - _cache["timestamp"]).total_seconds()
        if age < _cache["ttl_seconds"]:
            return _cache["data"]

    fees = []
    for chain in CHAINS:
        stats = fetch_chain_stats(chain)
        if stats:
            fee_data = parse_fee_data(chain, stats)
            if fee_data and fee_data["fee_usd"]:
                fees.append(fee_data)

    fees.sort(key=lambda x: x["fee_usd"])
    _cache["data"] = fees
    _cache["timestamp"] = now
    return fees

def fetch_chain_stats(chain):
    url = f"https://api.blockchair.com/{chain}/stats?key={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json().get("data", {})
        return None
    except Exception:
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
        "tagline": "Find the cheapest chain, every time",
        "docs": "/docs",
        "endpoints": [
            "/api/gas-fees/latest",
            "/api/gas-fees/cheapest",
            "/api/gas-fees/comparison"
        ]
    }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "FeeScout API", "version": "1.0.0"}

@app.get("/api/gas-fees/latest")
async def get_latest_fees():
    fees = get_cached_fees()
    return {
        "success": True,
        "count": len(fees),
        "data": [
            {
                "chain": f["chain"],
                "fee_usd": round(f["fee_usd"], 6),
                "fee_native": f["fee_native"],
                "fee_type": f["fee_type"],
                "timestamp": datetime.now().isoformat()
            }
            for f in fees
        ],
        "updated_at": datetime.now().isoformat()
    }

@app.get("/api/gas-fees/cheapest")
async def get_cheapest(limit: int = 5):
    fees = get_cached_fees()
    cheapest = [
        {"rank": i + 1, "chain": f["chain"], "fee_usd": round(f["fee_usd"], 6)}
        for i, f in enumerate(fees[:limit])
    ]
    return {"success": True, "data": cheapest}

@app.get("/api/gas-fees/comparison")
async def get_comparison(amount: float = 1000):
    fees = get_cached_fees()
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

# --- Checkout endpoint ---
from fastapi import Request

PLAN_PRICES = {
    "hobbyist": {"name": "Hobbyist", "price": 39, "description": "All chains + alerts", "square_link_env": "SQUARE_HOBBYIST_LINK"},
    "trader": {"name": "Trader", "price": 99, "description": "Real-time + API + webhooks", "square_link_env": "SQUARE_TRADER_LINK"},
}

@app.post("/api/create-checkout")
async def create_checkout(request: Request):
    form = await request.form()
    plan_key = form.get("plan", "hobbyist").lower()
    plan = PLAN_PRICES.get(plan_key)
    if not plan:
        return {"success": False, "error": "Invalid plan"}

    link = os.getenv(plan["square_link_env"], "")

    if link:
        return Response(status_code=303, headers={"Location": link})

    return HTMLResponse(content=f"""
    <html><body style="font-family:Inter,sans-serif;text-align:center;padding:80px;">
    <h1>FeeScout Checkout</h1>
    <h2>{plan['name']} Plan - ${plan['price']}/mo</h2>
    <p>{plan['description']}</p>
    <p style="color:#666;margin-top:40px;">Square payments coming soon. Set {plan['square_link_env']} env var to enable.</p>
    <a href="/" style="color:#3B82F6;">Back to FeeScout</a>
    </body></html>
    """)

# --- Serve frontend ---
@app.get("/landing", response_class=HTMLResponse)
async def serve_frontend():
    html_path = os.path.join(os.path.dirname(__file__), "..", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>FeeScout</h1><p>API is running. See <a href='/docs'>/docs</a></p>")

handler = app
