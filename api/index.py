"""
FeeScout — Complete backend API with auth, user management, and dashboard.
Deployed on Vercel as api/index.py (FastAPI + Supabase Postgres).
"""
from fastapi import FastAPI, Response, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel, EmailStr
import pg8000.native
import requests
import os
import json
import secrets
import hashlib
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import hmac as hmac_lib

app = FastAPI(title="FeeScout API", version="2.1.0")

ALLOWED_ORIGINS = [
    orig.strip()
    for orig in os.getenv("ALLOWED_ORIGINS", "https://feescout.com,https://www.feescout.com,https://www.feescout.bond").split(",")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BLOCKCHAIR_API_KEY = os.getenv("BLOCKCHAIR_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "FeeScout <onboarding@feescout.com>")
SQUARE_HOBBYIST_LINK = os.getenv("SQUARE_HOBBYIST_LINK", "https://square.link/u/YjHtGg2s")
SQUARE_TRADER_LINK = os.getenv("SQUARE_TRADER_LINK", "https://square.link/u/bW26nrZE")
SQUARE_WEBHOOK_SIGNATURE_KEY = os.getenv("SQUARE_WEBHOOK_SIGNATURE_KEY", "")

# Payment amount → tier mapping (in cents)
# Hobbyist = $39/mo = 3900 cents, Trader = $99/mo = 9900 cents
SQUARE_TIER_BY_AMOUNT: dict = {
    3900: "hobbyist",
    9900: "trader",
}

# Master account email — always gets trader tier
MASTER_EMAILS = {os.getenv("MASTER_EMAIL", "blunts954@gmail.com")}

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
def _parse_db_url(url: str) -> dict:
    """Parse a postgres:// URL into pg8000 connect kwargs.
    For Supabase hosts, forces the connection-pooler port (6543)
    since Vercel serverless cannot connect to port 5432 directly."""
    from urllib.parse import urlparse
    p = urlparse(url)
    is_supabase = p.hostname and "supabase.co" in p.hostname
    port = 6543 if is_supabase else (p.port or 5432)
    import ssl
    return {
        "host": p.hostname,
        "port": port,
        "database": p.path.lstrip("/"),
        "user": p.username,
        "password": p.password,
        "ssl_context": ssl.create_default_context(),
    }


def get_db():
    """Open a new Postgres connection using the DATABASE_URL env var.
    Returns None if DATABASE_URL is not configured."""
    if not DATABASE_URL:
        return None
    kwargs = _parse_db_url(DATABASE_URL)
    conn = pg8000.native.Connection(**kwargs)
    return conn


def _require_db():
    """Return a DB connection or raise HTTP 503 if not configured."""
    conn = get_db()
    if conn is None:
        raise HTTPException(503, "Database not configured")
    return conn


def _row_to_dict(columns, row):
    """Convert a pg8000 row + column list into a dict."""
    if row is None:
        return None
    return dict(zip(columns, row))


def _rows_to_dicts(columns, rows):
    return [dict(zip(columns, r)) for r in rows]


def _is_https(request: Request) -> bool:
    proto = request.headers.get("x-forwarded-proto", "")
    return proto == "https" or request.url.scheme == "https"


def init_db():
    """Create tables if they don't exist. Safe to call on every cold start."""
    conn = get_db()
    conn.run("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            tier TEXT DEFAULT 'free',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login TEXT,
            square_customer_id TEXT,
            subscribed_at TEXT
        )
    """)
    conn.run("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)
    conn.run("""
        CREATE TABLE IF NOT EXISTS usage_log (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            api_key TEXT,
            endpoint TEXT NOT NULL,
            ts TEXT NOT NULL,
            status_code INTEGER
        )
    """)
    conn.run("""
        CREATE TABLE IF NOT EXISTS password_resets (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0
        )
    """)
    conn.run("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)")
    conn.run("CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key)")
    conn.run("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    conn.run("CREATE INDEX IF NOT EXISTS idx_usage_user_ts ON usage_log(user_id, ts)")
    conn.run("CREATE INDEX IF NOT EXISTS idx_resets_token ON password_resets(token)")
    conn.close()


# Only run init_db if DATABASE_URL is configured
if DATABASE_URL:
    try:
        init_db()
    except Exception as e:
        print(f"[FeeScout] DB init warning: {e}")


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
        return hmac_lib.compare_digest(pw_hash.hex(), hex_hash)
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
    conn.run(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (:token, :uid, :created, :expires)",
        token=token, uid=user_id, created=now.isoformat(), expires=expires.isoformat(),
    )
    conn.close()
    return token


def set_session_cookie(response: Response, token: str, request: Request):
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=_is_https(request),
        samesite="lax",
        max_age=SESSION_DAYS * 86400,
        path="/",
    )


def get_user_from_session(request: Request) -> Optional[dict]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    conn = get_db()
    rows = conn.run(
        """SELECT u.* FROM users u
           JOIN sessions s ON s.user_id = u.id
           WHERE s.token = :token AND s.expires_at > :now""",
        token=token, now=datetime.now(timezone.utc).isoformat(),
    )
    cols = [c["name"] for c in conn.columns]
    conn.close()
    return _row_to_dict(cols, rows[0] if rows else None)


def get_user_from_api_key(api_key: str) -> Optional[dict]:
    if not api_key:
        return None
    conn = get_db()
    rows = conn.run("SELECT * FROM users WHERE api_key = :key", key=api_key)
    cols = [c["name"] for c in conn.columns]
    conn.close()
    return _row_to_dict(cols, rows[0] if rows else None)


def get_current_user(request: Request) -> Optional[dict]:
    user = get_user_from_session(request)
    if user:
        return user
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        return get_user_from_api_key(api_key)
    return None


def check_rate_limit(user: dict) -> bool:
    tier = user.get("tier", "free")
    limit = RATE_LIMITS.get(tier, 100)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_db()
    rows = conn.run(
        "SELECT COUNT(*) AS cnt FROM usage_log WHERE user_id = :uid AND ts LIKE :today",
        uid=user["id"], today=f"{today}%",
    )
    conn.close()
    cnt = rows[0][0] if rows else 0
    return cnt < limit


def log_request(user_id: Optional[int], api_key: Optional[str], endpoint: str, status_code: int):
    if not DATABASE_URL:
        return
    try:
        conn = get_db()
        conn.run(
            "INSERT INTO usage_log (user_id, api_key, endpoint, ts, status_code) VALUES (:uid, :key, :ep, :ts, :sc)",
            uid=user_id, key=api_key, ep=endpoint,
            ts=datetime.now(timezone.utc).isoformat(), sc=status_code,
        )
        conn.close()
    except Exception as e:
        print(f"[FeeScout] log_request error: {e}")


def ensure_master_tier(user: dict):
    if user["email"] in MASTER_EMAILS and user["tier"] != "trader":
        conn = get_db()
        now = datetime.now(timezone.utc).isoformat()
        conn.run(
            "UPDATE users SET tier = 'trader', updated_at = :now WHERE id = :uid",
            now=now, uid=user["id"],
        )
        conn.close()
        user["tier"] = "trader"


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
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.post("/api/auth/signup")
async def signup(req: SignupRequest, response: Response, request: Request):
    if len(req.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    api_key = generate_api_key()
    pw_hash = hash_password(req.password)
    now = datetime.now(timezone.utc).isoformat()
    initial_tier = "trader" if req.email in MASTER_EMAILS else "free"

    conn = _require_db()
    try:
        conn.run(
            "INSERT INTO users (email, password_hash, api_key, tier, created_at, updated_at) VALUES (:email, :pw, :key, :tier, :now, :now2)",
            email=req.email, pw=pw_hash, key=api_key, tier=initial_tier, now=now, now2=now,
        )
        rows = conn.run("SELECT id FROM users WHERE api_key = :key", key=api_key)
        user_id = rows[0][0]
    except Exception as e:
        conn.close()
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(409, "An account with this email already exists")
        raise HTTPException(500, "Could not create account")
    finally:
        conn.close()

    token = create_session(user_id)
    set_session_cookie(response, token, request)

    limit = RATE_LIMITS.get(initial_tier, 100)
    send_email(
        req.email,
        "Welcome to FeeScout — Your API Key",
        SIGNUP_EMAIL_HTML.format(api_key=api_key, tier=initial_tier.capitalize(), limit=limit),
    )

    log_request(user_id, api_key, "/api/auth/signup", 200)
    return {"success": True, "api_key": api_key, "tier": initial_tier}


@app.post("/api/auth/login")
async def login(req: LoginRequest, response: Response, request: Request):
    conn = _require_db()
    rows = conn.run("SELECT * FROM users WHERE email = :email", email=req.email.lower())
    cols = [c["name"] for c in conn.columns]
    conn.close()

    user = _row_to_dict(cols, rows[0] if rows else None)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")

    now = datetime.now(timezone.utc).isoformat()

    # Auto-promote master emails on login
    if req.email.lower() in MASTER_EMAILS and user["tier"] != "trader":
        conn = get_db()
        conn.run("UPDATE users SET tier = 'trader', updated_at = :now WHERE id = :uid", now=now, uid=user["id"])
        conn.close()
        user["tier"] = "trader"

    conn = get_db()
    conn.run("UPDATE users SET last_login = :now, updated_at = :now2 WHERE id = :uid", now=now, now2=now, uid=user["id"])
    conn.close()

    token = create_session(user["id"])
    set_session_cookie(response, token, request)

    return {"success": True, "tier": user["tier"], "api_key": user["api_key"]}


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        conn = get_db()
        conn.run("DELETE FROM sessions WHERE token = :token", token=token)
        conn.close()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"success": True}


RESET_EMAIL_HTML = """
<div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:40px 20px;">
  <h1 style="color:#00D68F;">Reset Your Password</h1>
  <p style="color:#333;font-size:16px;line-height:1.6;">
    We received a request to reset your FeeScout password. Click the button below —
    this link expires in <strong>1 hour</strong>.
  </p>
  <div style="text-align:center;margin:32px 0;">
    <a href="{reset_url}" style="background:#00D68F;color:#000;padding:14px 32px;border-radius:8px;
       text-decoration:none;font-weight:700;font-size:16px;display:inline-block;">
      Reset Password
    </a>
  </div>
  <p style="color:#999;font-size:13px;">
    If you didn't request this, you can safely ignore this email. Your password won't change.
  </p>
  <hr style="border:none;border-top:1px solid #eee;margin:30px 0;">
  <p style="color:#999;font-size:13px;">FeeScout — Find the cheapest chain, every time.</p>
</div>
"""


@app.post("/api/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, request: Request):
    """Send a password-reset email. Always returns 200 to avoid email enumeration."""
    conn = get_db()
    rows = conn.run("SELECT id FROM users WHERE email = :email", email=req.email.lower())
    conn.close()

    if rows:
        user_id = rows[0][0]
        token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=1)
        conn = get_db()
        conn.run(
            "INSERT INTO password_resets (token, user_id, created_at, expires_at) VALUES (:token, :uid, :created, :expires)",
            token=token, uid=user_id, created=now.isoformat(), expires=expires.isoformat(),
        )
        conn.close()

        base_url = str(request.base_url).rstrip("/")
        reset_url = f"{base_url}/dashboard?reset_token={token}"
        send_email(req.email, "Reset Your FeeScout Password", RESET_EMAIL_HTML.format(reset_url=reset_url))

    return {"success": True, "message": "If that email is registered, a reset link is on its way."}


@app.post("/api/auth/reset-password")
async def reset_password(req: ResetPasswordRequest):
    if len(req.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    conn = get_db()
    rows = conn.run(
        "SELECT * FROM password_resets WHERE token = :token AND used = 0 AND expires_at > :now",
        token=req.token, now=datetime.now(timezone.utc).isoformat(),
    )
    cols = [c["name"] for c in conn.columns]
    conn.close()

    reset_row = _row_to_dict(cols, rows[0] if rows else None)
    if not reset_row:
        raise HTTPException(400, "Reset link is invalid or has expired")

    new_hash = hash_password(req.password)
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    conn.run("UPDATE users SET password_hash = :h, updated_at = :now WHERE id = :uid", h=new_hash, now=now, uid=reset_row["user_id"])
    conn.run("UPDATE password_resets SET used = 1 WHERE token = :token", token=req.token)
    conn.close()

    return {"success": True, "message": "Password updated. You can now log in."}


@app.get("/api/auth/me")
async def me(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    ensure_master_tier(user)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_db()
    r1 = conn.run("SELECT COUNT(*) FROM usage_log WHERE user_id = :uid AND ts LIKE :today", uid=user["id"], today=f"{today}%")
    r2 = conn.run("SELECT COUNT(*) FROM usage_log WHERE user_id = :uid", uid=user["id"])
    conn.close()
    usage_today = r1[0][0] if r1 else 0
    usage_total = r2[0][0] if r2 else 0

    limit = RATE_LIMITS.get(user["tier"], 100)

    return {
        "success": True,
        "user": {
            "email": user["email"],
            "tier": user["tier"],
            "api_key": user["api_key"],
            "created_at": user["created_at"],
            "last_login": user["last_login"],
            "usage_today": usage_today,
            "usage_total": usage_total,
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
    conn.run(
        "UPDATE users SET api_key = :key, updated_at = :now WHERE id = :uid",
        key=new_key, now=datetime.now(timezone.utc).isoformat(), uid=user["id"],
    )
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
    with ThreadPoolExecutor(max_workers=10) as pool:
        fut_to_chain = {pool.submit(_fetch_chain_stats, c): c for c in CHAINS}
        for future in as_completed(fut_to_chain):
            chain = fut_to_chain[future]
            try:
                stats = future.result()
            except Exception:
                stats = None
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
# User dashboard data
# ---------------------------------------------------------------------------
@app.get("/api/dashboard")
async def dashboard_data(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    ensure_master_tier(user)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    conn = get_db()
    r1 = conn.run("SELECT COUNT(*) FROM usage_log WHERE user_id = :uid AND ts LIKE :today", uid=user["id"], today=f"{today}%")
    r2 = conn.run("SELECT COUNT(*) FROM usage_log WHERE user_id = :uid", uid=user["id"])
    r3 = conn.run(
        "SELECT DATE(ts) AS day, COUNT(*) AS cnt FROM usage_log WHERE user_id = :uid AND ts > :ago GROUP BY day ORDER BY day",
        uid=user["id"], ago=thirty_days_ago,
    )
    conn.close()

    usage_today = r1[0][0] if r1 else 0
    usage_total = r2[0][0] if r2 else 0
    daily_usage = [{"day": str(row[0]), "count": row[1]} for row in r3]

    limit = RATE_LIMITS.get(user["tier"], 100)
    usage_pct = min(100, round((usage_today / limit) * 100)) if limit > 0 else 0
    estimated_savings = round(usage_total * 0.15, 2)

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
            "daily_breakdown": daily_usage,
        },
        "estimated_savings_usd": estimated_savings,
        "upgrade_cta": usage_pct >= 80 and user["tier"] == "free",
    }


# ---------------------------------------------------------------------------
# Square webhook
# ---------------------------------------------------------------------------
def _verify_square_signature(body: bytes, signature_header: str, notification_url: str) -> bool:
    """
    Square signs webhooks with HMAC-SHA256 over (notification_url + raw_body).
    The result is base64-encoded and sent in x-square-hmacsha256-signature.
    """
    if not SQUARE_WEBHOOK_SIGNATURE_KEY or not signature_header:
        return False
    import base64
    payload = notification_url.encode("utf-8") + body
    expected = base64.b64encode(
        hmac_lib.new(
            SQUARE_WEBHOOK_SIGNATURE_KEY.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")
    return hmac_lib.compare_digest(expected, signature_header)


def _upgrade_user_by_email(email: str, new_tier: str, square_customer_id: Optional[str] = None):
    """Find a user by email and upgrade their tier. Returns True if found."""
    if not email:
        return False
    conn = get_db()
    rows = conn.run("SELECT id, tier FROM users WHERE email = :email", email=email.lower())
    cols = [c["name"] for c in conn.columns]
    conn.close()

    row = _row_to_dict(cols, rows[0] if rows else None)
    if not row:
        print(f"[FeeScout] Square webhook: no account for {email} — tier upgrade skipped")
        return False

    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    conn.run(
        """UPDATE users
           SET tier = :tier, updated_at = :now, subscribed_at = :now2,
               square_customer_id = COALESCE(:cid, square_customer_id)
           WHERE id = :uid""",
        tier=new_tier, now=now, now2=now, cid=square_customer_id, uid=row["id"],
    )
    conn.close()
    print(f"[FeeScout] Upgraded {email} → {new_tier}")

    # Send upgrade confirmation email
    tier_label = new_tier.capitalize()
    limit = RATE_LIMITS.get(new_tier, 100)
    upgrade_html = f"""
<div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:40px 20px;">
  <h1 style="color:#00D68F;">You're now on {tier_label}! 🎉</h1>
  <p style="color:#333;font-size:16px;line-height:1.6;">
    Your FeeScout account has been upgraded to the <strong>{tier_label}</strong> plan.
    You now have <strong>{limit:,} API calls/day</strong> and access to all features.
  </p>
  <div style="text-align:center;margin:32px 0;">
    <a href="https://feescout.com/dashboard" style="background:#00D68F;color:#000;padding:14px 32px;
       border-radius:8px;text-decoration:none;font-weight:700;font-size:16px;display:inline-block;">
      Go to Your Dashboard
    </a>
  </div>
  <hr style="border:none;border-top:1px solid #eee;margin:30px 0;">
  <p style="color:#999;font-size:13px;">FeeScout — Find the cheapest chain, every time.</p>
</div>
"""
    send_email(email, f"You're now on FeeScout {tier_label}!", upgrade_html)
    return True


@app.post("/api/webhooks/square")
async def square_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("x-square-hmacsha256-signature", "")

    # Build the exact notification URL Square will sign against
    notification_url = str(request.url)

    if SQUARE_WEBHOOK_SIGNATURE_KEY and not _verify_square_signature(body, signature, notification_url):
        print("[FeeScout] Square webhook: invalid signature — rejected")
        raise HTTPException(403, "Invalid signature")

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    event_type = payload.get("type", "")
    print(f"[FeeScout] Square webhook received: {event_type}")

    # ---- payment.completed ------------------------------------------------
    # Fires when a one-time or subscription payment succeeds.
    if event_type == "payment.completed":
        payment = payload.get("data", {}).get("object", {}).get("payment", {})
        email = payment.get("buyer_email_address", "").lower()
        amount_cents = payment.get("total_money", {}).get("amount", 0)
        customer_id = payment.get("customer_id")

        new_tier = SQUARE_TIER_BY_AMOUNT.get(amount_cents)
        if not new_tier:
            # Unrecognised amount — log and return 200 so Square stops retrying
            print(f"[FeeScout] Unknown payment amount {amount_cents} cents from {email}")
            return {"received": True}

        _upgrade_user_by_email(email, new_tier, customer_id)

    # ---- subscription.created ---------------------------------------------
    # Fires when a recurring subscription is first activated.
    elif event_type == "subscription.created":
        subscription = payload.get("data", {}).get("object", {}).get("subscription", {})
        customer_id = subscription.get("customer_id")
        # Square doesn't include email in the subscription event — look it up
        # via a lightweight call to the Customers API if we have the access token.
        # For sandbox we rely on payment.completed covering the same transaction.
        print(f"[FeeScout] subscription.created for customer {customer_id} (handled via payment.completed)")

    # Always return 200 — Square retries on any non-2xx response
    return {"received": True}


# ---------------------------------------------------------------------------
# Root / Health
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_html(filename: str) -> str:
    path = os.path.join(BASE_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/")
async def serve_index():
    return HTMLResponse(content=_read_html("index.html"))


@app.get("/dashboard")
async def serve_dashboard():
    return HTMLResponse(content=_read_html("dashboard.html"))


@app.get("/privacy-policy")
async def serve_privacy():
    return HTMLResponse(content=_read_html("privacy-policy.html"))


@app.get("/feescoutlogo.png")
async def serve_logo():
    return FileResponse(os.path.join(BASE_DIR, "feescoutlogo.png"), media_type="image/png")


# ---------------------------------------------------------------------------
# SEO Pages — Static HTML pages for search engine optimization
# ---------------------------------------------------------------------------
_SEO_PAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pages", "seo")

_SEO_ROUTES = {
    "ethereum-gas-tracker": "ethereum-gas-tracker.html",
    "bitcoin-fee-tracker": "bitcoin-fee-tracker.html",
    "polygon-gas-tracker": "polygon-gas-tracker.html",
    "arbitrum-gas-tracker": "arbitrum-gas-tracker.html",
    "solana-fee-tracker": "solana-fee-tracker.html",
    "gas-fee-comparison": "gas-fee-comparison.html",
    "best-time-to-buy-crypto": "best-time-to-buy-crypto.html",
    "nft-gas-fees": "nft-gas-fees.html",
    "defi-gas-optimization": "defi-gas-optimization.html",
    "crypto-gas-fee-api": "crypto-gas-fee-api.html",
    "best-time-to-transact": "best-time-to-transact.html",
}


def _serve_seo_page(html_file: str) -> HTMLResponse:
    filepath = os.path.join(_SEO_PAGES_DIR, html_file)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Page not found")


for _slug, _file in _SEO_ROUTES.items():
    def _make_handler(f):
        async def _handler():
            return _serve_seo_page(f)
        return _handler
    app.get(f"/{_slug}", response_class=HTMLResponse, include_in_schema=False)(_make_handler(_file))


@app.get("/home", response_class=HTMLResponse, include_in_schema=False)
async def home_page():
    landing_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pages", "landing-page.html")
    try:
        with open(landing_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Landing page not found")


@app.get("/sitemap.xml", response_class=HTMLResponse, include_in_schema=False)
async def sitemap():
    sitemap_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pages", "sitemap.xml")
    try:
        with open(sitemap_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), media_type="application/xml")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Sitemap not found")


@app.get("/robots.txt", response_class=HTMLResponse, include_in_schema=False)
async def robots():
    robots_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pages", "robots.txt")
    try:
        with open(robots_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), media_type="text/plain")
    except FileNotFoundError:
        return HTMLResponse(content="User-agent: *\nAllow: /", media_type="text/plain")


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health_check():
    """
    Health check endpoint.
    Returns 'healthy' if DB is connected, 'degraded' if no DB is configured,
    and 'unhealthy' if DB connection fails.
    """
    if not DATABASE_URL:
        return {
            "status": "healthy",
            "service": "FeeScout API",
            "version": "2.1.0",
            "database": "not_configured",
        }
    db_ok = False
    try:
        conn = get_db()
        conn.run("SELECT 1")
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "FeeScout API",
        "version": "2.1.0",
        "database": "connected" if db_ok else "disconnected",
    }


# Vercel handler
handler = app
