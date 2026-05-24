"""
FeeScout — Complete backend API with auth, user management, and dashboard.
Deployed on Vercel as api/index.py (FastAPI).
"""
from fastapi import FastAPI, Response, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel, EmailStr
import requests
import sqlite3
import os
import json
import secrets
import hashlib
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
import hmac

app = FastAPI(title="FeeScout API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BLOCKCHAIR_API_KEY = os.getenv("BLOCKCHAIR_API_KEY", "")
DATABASE_PATH = "/tmp/feescout.db"  # Vercel writable directory
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "FeeScout <onboarding@feescout.com>")
SQUARE_HOBBYIST_LINK = os.getenv("SQUARE_HOBBYIST_LINK", "")
SQUARE_TRADER_LINK = os.getenv("SQUARE_TRADER_LINK", "")

# Rate limits per tier (requests per day)
RATE_LIMITS = {
    "free": 100,
    "hobbyist": 10000,
    "trader": 100000,
}

# Session cookie settings
SESSION_COOKIE = "fs_session"
SESSION_DAYS = 30

# Chains to fetch from Blockchair
CHAINS = [
    "bitcoin", "bitcoin-cash", "litecoin", "bitcoin-sv", "dogecoin",
    "dash", "ripple", "groestlcoin", "stellar", "monero", "cardano",
    "zcash", "mixin", "tezos", "eos", "ethereum", "polygon",
    "arbitrum", "optimism", "base", "avalanche", "fantom",
    "bnb", "moonbeam", "cronos", "gnosis", "ecash", "solana",
]

# In-memory fee cache
_fee_cache: dict = {"data": None, "timestamp": None, "ttl_seconds": 60}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist. Safe to call on every cold start."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            tier TEXT DEFAULT 'free',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login TEXT,
            square_customer_id TEXT,
            subscribed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            api_key TEXT,
            endpoint TEXT NOT NULL,
            ts TEXT NOT NULL,
            status_code INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
        CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_usage_user_ts ON usage_log(user_id, ts);
    """)
    conn.close()


init_db()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${pw_hash.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, hex_hash = stored.split("$", 1)
        pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return hmac.compare_digest(pw_hash.hex(), hex_hash)
    except Exception:
        return False


def generate_api_key() -> str:
    return f"fs_{secrets.token_urlsafe(32)}"


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def create_session(user_id: int) -> str:
    token = generate_session_token()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=SESSION_DAYS)
    conn = get_db()
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, user_id, now.isoformat(), expires.isoformat()),
    )
    conn.commit()
    conn.close()
    return token


def get_user_from_session(request: Request) -> Optional[dict]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    conn = get_db()
    row = conn.execute(
        """SELECT u.* FROM users u
           JOIN sessions s ON s.user_id = u.id
           WHERE s.token = ? AND s.expires_at > ?""",
        (token, datetime.now(timezone.utc).isoformat()),
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_user_from_api_key(api_key: str) -> Optional[dict]:
    if not api_key:
        return None
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE api_key = ?", (api_key,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_current_user(request: Request) -> Optional[dict]:
    """Check session cookie first, then API key header."""
    user = get_user_from_session(request)
    if user:
        return user
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        return get_user_from_api_key(api_key)
    return None


def check_rate_limit(user: dict) -> bool:
    """Return True if the user is within their daily rate limit."""
    tier = user.get("tier", "free")
    limit = RATE_LIMITS.get(tier, 100)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM usage_log WHERE user_id = ? AND ts LIKE ?",
        (user["id"], f"{today}%"),
    ).fetchone()
    conn.close()
    return row["cnt"] < limit


def log_request(user_id: Optional[int], api_key: Optional[str], endpoint: str, status_code: int):
    conn = get_db()
    conn.execute(
        "INSERT INTO usage_log (user_id, api_key, endpoint, ts, status_code) VALUES (?, ?, ?, ?, ?)",
        (user_id, api_key, endpoint, datetime.now(timezone.utc).isoformat(), status_code),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Email helper (Resend)
# ---------------------------------------------------------------------------
def send_email(to: str, subject: str, html: str) -> bool:
    if not RESEND_API_KEY:
        return False
    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json={"from": RESEND_FROM, "to": [to], "subject": subject, "html": html},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


SIGNUP_EMAIL_HTML = """
<div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:40px 20px;">
  <h1 style="color:#00D68F;">Welcome to FeeScout!</h1>
  <p style="color:#333;font-size:16px;line-height:1.6;">
    You're all set. Here's your API key:
  </p>
  <div style="background:#f4f4f4;border:1px solid #ddd;border-radius:8px;padding:16px;margin:20px 0;font-family:monospace;word-break:break-all;">
    {api_key}
  </div>
  <p style="color:#333;font-size:16px;line-height:1.6;">
    Use it in your requests:
  </p>
  <pre style="background:#1a1a2e;color:#00D68F;padding:16px;border-radius:8px;overflow-x:auto;">
curl -H "X-API-Key: {api_key}" \\
  https://feescout.com/api/gas-fees/latest</pre>
  <p style="color:#333;font-size:16px;line-height:1.6;">
    You're on the <strong>{tier}</strong> tier with <strong>{limit} API calls/day</strong>.
    <a href="https://feescout.com/#pricing" style="color:#3B82F6;">Upgrade anytime</a>.
  </p>
  <hr style="border:none;border-top:1px solid #eee;margin:30px 0;">
  <p style="color:#999;font-size:13px;">
    FeeScout — Find the cheapest chain, every time.
  </p>
</div>
"""


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class SignupRequest(BaseModel):
    email: EmailStr
    password: str  # min 8 chars enforced in validation


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.post("/api/auth/signup")
async def signup(req: SignupRequest, response: Response):
    if len(req.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    api_key = generate_api_key()
    pw_hash = hash_password(req.password)
    now = datetime.now(timezone.utc).isoformat()

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (email, password_hash, api_key, tier, created_at, updated_at) VALUES (?, ?, ?, 'free', ?, ?)",
            (req.email, pw_hash, api_key, now, now),
        )
        conn.commit()
        user_id = conn.execute("SELECT id FROM users WHERE api_key = ?", (api_key,)).fetchone()["id"]
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(409, "An account with this email already exists")
    conn.close()

    # Create session
    token = create_session(user_id)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=SESSION_DAYS * 86400,
    )

    # Send welcome email
    send_email(
        req.email,
        "Welcome to FeeScout — Your API Key",
        SIGNUP_EMAIL_HTML.format(api_key=api_key, tier="Free", limit=100),
    )

    log_request(user_id, api_key, "/api/auth/signup", 200)

    return {"success": True, "api_key": api_key, "tier": "free"}


@app.post("/api/auth/login")
async def login(req: LoginRequest, response: Response):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (req.email,)).fetchone()
    conn.close()

    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(401, "Invalid email or password")

    # Update last login
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    conn.execute("UPDATE users SET last_login = ?, updated_at = ? WHERE id = ?", (now, now, row["id"]))
    conn.commit()
    conn.close()

    # Create session
    token = create_session(row["id"])
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=SESSION_DAYS * 86400,
    )

    return {"success": True, "tier": row["tier"], "api_key": row["api_key"]}


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        conn = get_db()
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
    response.delete_cookie(SESSION_COOKIE)
    return {"success": True}


@app.get("/api/auth/me")
async def me(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    # Get today's usage
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_db()
    usage_row = conn.execute(
        "SELECT COUNT(*) as cnt FROM usage_log WHERE user_id = ? AND ts LIKE ?",
        (user["id"], f"{today}%"),
    ).fetchone()
    total_row = conn.execute(
        "SELECT COUNT(*) as cnt FROM usage_log WHERE user_id = ?",
        (user["id"],),
    ).fetchone()
    conn.close()

    limit = RATE_LIMITS.get(user["tier"], 100)

    return {
        "success": True,
        "user": {
            "email": user["email"],
            "tier": user["tier"],
            "api_key": user["api_key"],
            "created_at": user["created_at"],
            "last_login": user["last_login"],
            "usage_today": usage_row["cnt"],
            "usage_total": total_row["cnt"],
            "daily_limit": limit,
        },
    }


@app.post("/api/auth/rotate-key")
async def rotate_key(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    new_key = generate_api_key()
    conn = get_db()
    conn.execute(
        "UPDATE users SET api_key = ?, updated_at = ? WHERE id = ?",
        (new_key, datetime.now(timezone.utc).isoformat(), user["id"]),
    )
    conn.commit()
    conn.close()

    return {"success": True, "api_key": new_key}


# ---------------------------------------------------------------------------
# Gas fee data (Blockchair)
# ---------------------------------------------------------------------------
def get_cached_fees():
    now = datetime.now(timezone.utc)
    if _fee_cache["data"] and _fee_cache["timestamp"]:
        age = (now - _fee_cache["timestamp"]).total_seconds()
        if age < _fee_cache["ttl_seconds"]:
            return _fee_cache["data"]

    fees = []
    for chain in CHAINS:
        stats = _fetch_chain_stats(chain)
        if stats:
            fee_data = _parse_fee_data(chain, stats)
            if fee_data and fee_data["fee_usd"]:
                fees.append(fee_data)

    fees.sort(key=lambda x: x["fee_usd"])
    _fee_cache["data"] = fees
    _fee_cache["timestamp"] = now
    return fees


def _fetch_chain_stats(chain: str):
    if not BLOCKCHAIR_API_KEY:
        return None
    url = f"https://api.blockchair.com/{chain}/stats?key={BLOCKCHAIR_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("data", {})
        return None
    except Exception:
        return None


def _parse_fee_data(chain: str, stats: dict):
    if not stats:
        return None
    fee_data = {"chain": chain, "fee_usd": None, "fee_native": None, "fee_type": None}
    if "suggested_transaction_fee_per_byte_sat" in stats:
        sat = stats["suggested_transaction_fee_per_byte_sat"]
        fee_data["fee_native"] = sat * 250 / 100_000_000
        fee_data["fee_type"] = "sat/byte"
        if "market_price_usd" in stats:
            fee_data["fee_usd"] = fee_data["fee_native"] * stats["market_price_usd"]
    elif "suggested_transaction_fee_gwei_options" in stats:
        options = stats["suggested_transaction_fee_gwei_options"]
        gwei = options.get("normal", 0)
        fee_data["fee_native"] = gwei * 21000 / 1_000_000_000
        fee_data["fee_type"] = "gwei"
        if "market_price_usd" in stats:
            fee_data["fee_usd"] = fee_data["fee_native"] * stats["market_price_usd"]
    elif chain == "solana" and "average_transaction_fee" in stats:
        fee_data["fee_native"] = stats["average_transaction_fee"] / 1_000_000_000
        fee_data["fee_type"] = "lamports"
        if "market_price_usd" in stats:
            fee_data["fee_usd"] = fee_data["fee_native"] * stats["market_price_usd"]
    elif "average_transaction_fee_usd" in stats:
        fee_data["fee_usd"] = stats["average_transaction_fee_usd"]
        fee_data["fee_type"] = "avg_usd"
    return fee_data


# ---------------------------------------------------------------------------
# Gas fee API endpoints
# ---------------------------------------------------------------------------
@app.get("/api/gas-fees/latest")
async def get_latest_fees(request: Request):
    fees = get_cached_fees()
    api_key = request.headers.get("X-API-Key", "")
    user = get_current_user(request)

    # Rate limit check for API key users
    if user and not check_rate_limit(user):
        log_request(user["id"], api_key, "/api/gas-fees/latest", 429)
        raise HTTPException(429, "Daily rate limit exceeded. Upgrade your plan at /#pricing")

    log_request(user["id"] if user else None, api_key, "/api/gas-fees/latest", 200)

    return {
        "success": True,
        "count": len(fees),
        "data": [
            {
                "chain": f["chain"],
                "fee_usd": round(f["fee_usd"], 6),
                "fee_native": f["fee_native"],
                "fee_type": f["fee_type"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            for f in fees
        ],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/gas-fees/cheapest")
async def get_cheapest(request: Request, limit: int = 5):
    fees = get_cached_fees()
    user = get_current_user(request)
    api_key = request.headers.get("X-API-Key", "")

    if user and not check_rate_limit(user):
        log_request(user["id"], api_key, "/api/gas-fees/cheapest", 429)
        raise HTTPException(429, "Daily rate limit exceeded")

    log_request(user["id"] if user else None, api_key, "/api/gas-fees/cheapest", 200)

    return {
        "success": True,
        "data": [
            {"rank": i + 1, "chain": f["chain"], "fee_usd": round(f["fee_usd"], 6)}
            for i, f in enumerate(fees[:limit])
        ],
    }


@app.get("/api/gas-fees/comparison")
async def get_comparison(request: Request, amount: float = 1000):
    fees = get_cached_fees()
    user = get_current_user(request)
    api_key = request.headers.get("X-API-Key", "")

    if user and not check_rate_limit(user):
        log_request(user["id"], api_key, "/api/gas-fees/comparison", 429)
        raise HTTPException(429, "Daily rate limit exceeded")

    log_request(user["id"] if user else None, api_key, "/api/gas-fees/comparison", 200)

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
            "savings_percent": round(savings_pct, 2),
        })

    return {
        "success": True,
        "transfer_amount_usd": amount,
        "cheapest_option": cheapest["chain"],
        "comparisons": comparisons,
    }


# ---------------------------------------------------------------------------
# Checkout endpoints
# ---------------------------------------------------------------------------
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
        raise HTTPException(400, "Invalid plan")

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


# ---------------------------------------------------------------------------
# User dashboard data
# ---------------------------------------------------------------------------
@app.get("/api/dashboard")
async def dashboard_data(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_db()

    # Today's usage
    usage_today = conn.execute(
        "SELECT COUNT(*) as cnt FROM usage_log WHERE user_id = ? AND ts LIKE ?",
        (user["id"], f"{today}%"),
    ).fetchone()["cnt"]

    # Total usage
    usage_total = conn.execute(
        "SELECT COUNT(*) as cnt FROM usage_log WHERE user_id = ?",
        (user["id"],),
    ).fetchone()["cnt"]

    # Last 30 days usage per day
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    daily_usage = conn.execute(
        "SELECT date(ts) as day, COUNT(*) as cnt FROM usage_log WHERE user_id = ? AND ts > ? GROUP BY day ORDER BY day",
        (user["id"], thirty_days_ago),
    ).fetchall()

    conn.close()

    limit = RATE_LIMITS.get(user["tier"], 100)
    usage_pct = min(100, round((usage_today / limit) * 100)) if limit > 0 else 0

    # Estimate gas savings (simple heuristic based on usage)
    estimated_savings = round(usage_total * 0.15, 2)  # $0.15 avg savings per API call

    return {
        "success": True,
        "user": {
            "email": user["email"],
            "tier": user["tier"],
            "api_key": user["api_key"],
            "created_at": user["created_at"],
        },
        "usage": {
            "today": usage_today,
            "total": usage_total,
            "daily_limit": limit,
            "usage_pct": usage_pct,
            "daily_breakdown": [{"day": r["day"], "count": r["cnt"]} for r in daily_usage],
        },
        "estimated_savings_usd": estimated_savings,
        "upgrade_cta": usage_pct >= 80,
    }


# ---------------------------------------------------------------------------
# Serve frontend
# ---------------------------------------------------------------------------
@app.get("/landing", response_class=HTMLResponse)
async def serve_landing():
    html_path = os.path.join(os.path.dirname(__file__), "..", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>FeeScout</h1><p>API is running.</p>")


# Root redirects to landing
@app.get("/")
async def root():
    return {
        "service": "FeeScout API",
        "status": "healthy",
        "version": "2.0.0",
        "tagline": "Find the cheapest chain, every time",
        "docs": "/docs",
        "endpoints": [
            "/api/gas-fees/latest",
            "/api/gas-fees/cheapest",
            "/api/gas-fees/comparison",
            "/api/auth/signup",
            "/api/auth/login",
            "/api/auth/me",
            "/api/dashboard",
        ],
    }


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "FeeScout API", "version": "2.0.0"}


# Vercel handler
handler = app
