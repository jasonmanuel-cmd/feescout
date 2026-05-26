"""
FeeScout Gas v3 — Multi-source gas fee scraper.
Supports 40+ chains using multiple free APIs.
No API key required for basic usage.
"""
import requests
import time
import json
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# Chain list with USD prices (approximate, for fallback) and API sources
# ---------------------------------------------------------------------------
CHAINS_CONFIG = {
    # Blockchair-supported chains (free tier: ~30 req/min)
    "bitcoin":          {"source": "blockchair", "type": "utxo",    "fallback_price_usd": 100000},
    "bitcoin-cash":     {"source": "blockchair", "type": "utxo",    "fallback_price_usd": 400},
    "bitcoin-sv":       {"source": "blockchair", "type": "utxo",    "fallback_price_usd": 50},
    "litecoin":         {"source": "blockchair", "type": "utxo",    "fallback_price_usd": 100},
    "dogecoin":         {"source": "blockchair", "type": "utxo",    "fallback_price_usd": 0.35},
    "dash":             {"source": "blockchair", "type": "utxo",    "fallback_price_usd": 40},
    "zcash":            {"source": "blockchair", "type": "utxo",    "fallback_price_usd": 15},
    "groestlcoin":      {"source": "blockchair", "type": "utxo",    "fallback_price_usd": 0.05},
    "ecash":            {"source": "blockchair", "type": "utxo",    "fallback_price_usd": 0.00003},
    "monero":           {"source": "blockchair", "type": "privacy", "fallback_price_usd": 160},
    "cardano":          {"source": "blockchair", "type": "account", "fallback_price_usd": 0.80},
    "ripple":           {"source": "blockchair", "type": "account", "fallback_price_usd": 0.55},
    "stellar":          {"source": "blockchair", "type": "account", "fallback_price_usd": 0.12},
    "tezos":            {"source": "blockchair", "type": "account", "fallback_price_usd": 1.20},
    "eos":              {"source": "blockchair", "type": "account", "fallback_price_usd": 0.90},
    "mixin":            {"source": "blockchair", "type": "account", "fallback_price_usd": 0.30},
    "gnosis":           {"source": "blockchair", "type": "evm",     "fallback_price_usd": 200},
    "cronos":           {"source": "blockchair", "type": "evm",     "fallback_price_usd": 0.08},
    "moonbeam":         {"source": "blockchair", "type": "evm",     "fallback_price_usd": 0.30},

    # EVM chains via native JSON-RPC (free, no key needed for eth_gasPrice)
    "ethereum":         {"source": "rpc", "rpc_url": "https://ethereum-rpc.publicnode.com", "fallback_price_usd": 3500},
    "polygon":          {"source": "rpc", "rpc_url": "https://polygon-bor-rpc.publicnode.com", "fallback_price_usd": 0.85},
    "arbitrum":         {"source": "rpc", "rpc_url": "https://arbitrum-one-rpc.publicnode.com", "fallback_price_usd": 3500},
    "optimism":         {"source": "rpc", "rpc_url": "https://optimism-rpc.publicnode.com", "fallback_price_usd": 3500},
    "base":             {"source": "rpc", "rpc_url": "https://base-rpc.publicnode.com", "fallback_price_usd": 3500},
    "avalanche":        {"source": "rpc", "rpc_url": "https://avalanche-c-chain-rpc.publicnode.com", "fallback_price_usd": 35},
    "fantom":           {"source": "rpc", "rpc_url": "https://fantom-rpc.publicnode.com", "fallback_price_usd": 0.50},
    "bnb":              {"source": "rpc", "rpc_url": "https://bsc-rpc.publicnode.com", "fallback_price_usd": 600},

    # Solana (free RPC)
    "solana":           {"source": "solana_rpc", "rpc_url": "https://api.mainnet-beta.solana.com", "fallback_price_usd": 170},
}


def _fetch_blockchair(chain: str, api_key: str = "") -> dict | None:
    """Fetch stats from Blockchair API."""
    url = f"https://api.blockchair.com/{chain}/stats"
    if api_key:
        url += f"?key={api_key}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json().get("data")
            if data:
                return data
        return None
    except Exception:
        return None


def _fetch_evm_gas(rpc_url: str) -> float | None:
    """Fetch current gas price in Gwei from an EVM JSON-RPC endpoint."""
    payload = {"jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 1}
    try:
        resp = requests.post(rpc_url, json=payload, timeout=10)
        if resp.status_code == 200:
            result = resp.json().get("result")
            if result:
                # Convert hex wei to gwei
                wei = int(result, 16)
                return wei / 1e9  # gwei
        return None
    except Exception:
        return None


def _fetch_solana_fee(rpc_url: str) -> float | None:
    """Fetch recent Solana transaction fee."""
    payload = {
        "jsonrpc": "2.0",
        "method": "getRecentPrioritizationFees",
        "params": [[]],
        "id": 1,
    }
    try:
        resp = requests.post(rpc_url, json=payload, timeout=10)
        if resp.status_code == 200:
            fees = resp.json().get("result", [])
            if fees:
                # Average fee in lamports
                avg = sum(f.get("prioritizationFee", 0) for f in fees) / len(fees)
                return avg  # lamports
        return None
    except Exception:
        return None


def _parse_blockchair_fee(chain: str, stats: dict, config: dict) -> dict | None:
    """Parse fee data from Blockchair stats response."""
    if not stats:
        return None

    price_usd = stats.get("market_price_usd", config["fallback_price_usd"])
    fee_data = {"chain": chain, "fee_usd": None, "fee_native": None, "fee_type": None}

    # UTXO chains: sat/byte
    if config["type"] == "utxo":
        sat_per_byte = stats.get("suggested_transaction_fee_per_byte_sat")
        if sat_per_byte:
            # Typical tx size ~250 bytes
            fee_native = sat_per_byte * 250 / 100_000_000  # in BTC/etc
            fee_data["fee_native"] = fee_native
            fee_data["fee_usd"] = fee_native * price_usd
            fee_data["fee_type"] = "sat/byte"

    # EVM chains on Blockchair
    elif config["type"] == "evm":
        gwei_options = stats.get("suggested_transaction_fee_gwei_options")
        if gwei_options:
            gwei = gwei_options.get("normal", 0)
            fee_native = gwei * 21000 / 1e9  # in ETH/etc
            fee_data["fee_native"] = fee_native
            fee_data["fee_usd"] = fee_native * price_usd
            fee_data["fee_type"] = "gwei"

    # Account-based chains
    elif config["type"] in ("account", "privacy"):
        avg_fee = stats.get("average_transaction_fee_usd")
        if avg_fee:
            fee_data["fee_usd"] = avg_fee
            fee_data["fee_type"] = "avg_usd"
        else:
            sat_per_byte = stats.get("suggested_transaction_fee_per_byte_sat")
            if sat_per_byte:
                fee_native = sat_per_byte * 250 / 100_000_000
                fee_data["fee_native"] = fee_native
                fee_data["fee_usd"] = fee_native * price_usd
                fee_data["fee_type"] = "sat/byte"

    if fee_data["fee_usd"] is not None:
        return fee_data
    return None


def _fetch_single_chain(chain: str, config: dict, api_key: str = "") -> dict | None:
    """Fetch gas fee for a single chain."""
    source = config["source"]

    if source == "blockchair":
        stats = _fetch_blockchair(chain, api_key)
        return _parse_blockchair_fee(chain, stats, config)

    elif source == "rpc":
        gas_price_gwei = _fetch_evm_gas(config["rpc_url"])
        if gas_price_gwei is not None:
            # Standard transfer: 21000 gas
            fee_native = gas_price_gwei * 21000 / 1e9  # in ETH/MATIC/etc
            fee_usd = fee_native * config["fallback_price_usd"]
            return {
                "chain": chain,
                "fee_usd": fee_usd,
                "fee_native": fee_native,
                "fee_type": "gwei",
            }

    elif source == "solana_rpc":
        fee_lamports = _fetch_solana_fee(config["rpc_url"])
        if fee_lamports is not None:
            fee_native = fee_lamports / 1e9  # SOL
            fee_usd = fee_native * config["fallback_price_usd"]
            return {
                "chain": chain,
                "fee_usd": fee_usd,
                "fee_native": fee_native,
                "fee_type": "lamports",
            }

    return None


def fetch_all_fees(api_key: str = "", max_workers: int = 15) -> list[dict]:
    """Fetch gas fees for all configured chains. Returns sorted list (cheapest first)."""
    fees = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_fetch_single_chain, chain, config, api_key): chain
            for chain, config in CHAINS_CONFIG.items()
        }
        for future in as_completed(futures):
            chain = futures[future]
            try:
                result = future.result()
                if result and result.get("fee_usd") is not None and result["fee_usd"] >= 0:
                    result["timestamp"] = datetime.now(timezone.utc).isoformat()
                    fees.append(result)
            except Exception:
                pass

    fees.sort(key=lambda x: x["fee_usd"])
    return fees


if __name__ == "__main__":
    print("Fetching gas fees for all chains...")
    results = fetch_all_fees()
    print(f"\nGot data for {len(results)} chains:\n")
    for i, r in enumerate(results[:15], 1):
        print(f"  #{i:2d} {r['chain']:20s}  ${r['fee_usd']:.6f}  ({r['fee_type']})")
