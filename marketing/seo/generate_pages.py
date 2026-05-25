"""
FeeScout SEO Page Generator
Creates static HTML pages for search engine optimization.
These pages target high-intent keywords to drive organic traffic.
"""
from __future__ import annotations

import os
from typing import List, Tuple

# SEO page definitions: (slug, title, description, keywords, template)
SEO_PAGES: List[Tuple[str, str, str, str, str]] = [
    (
        "ethereum-gas-tracker",
        "Ethereum Gas Tracker — Live ETH Gas Prices | FeeScout",
        "Track Ethereum gas prices in real-time. See current gwei, historical trends, and get alerts when fees drop. Never overpay on ETH transactions again.",
        "ethereum gas tracker, eth gas price, ethereum gas fees, gwei tracker, eth transaction cost",
        "ethereum"
    ),
    (
        "bitcoin-fee-tracker",
        "Bitcoin Transaction Fee Tracker — Live BTC Fees | FeeScout",
        "Real-time Bitcoin transaction fee tracker. See current sat/vB rates, mempool size, and optimal fee targets for fast confirmation.",
        "bitcoin fee tracker, btc transaction fees, bitcoin mempool, sat per byte, btc gas fees",
        "bitcoin"
    ),
    (
        "polygon-gas-tracker",
        "Polygon Gas Tracker — Live MATIC Gas Prices | FeeScout",
        "Track Polygon (MATIC) gas fees in real-time. See current gas prices, historical data, and compare with Ethereum mainnet.",
        "polygon gas tracker, matic gas price, polygon transaction fees, polygon vs ethereum gas",
        "polygon"
    ),
    (
        "arbitrum-gas-tracker",
        "Arbitrum Gas Tracker — Live ARB L2 Fees | FeeScout",
        "Real-time Arbitrum gas fee tracker. Compare L2 fees with Ethereum mainnet and find the cheapest time to bridge and transact.",
        "arbitrum gas tracker, arbitrum fees, arbitrum vs ethereum, L2 gas prices, arbitrum bridge cost",
        "arbitrum"
    ),
    (
        "solana-fee-tracker",
        "Solana Fee Tracker — Live SOL Transaction Costs | FeeScout",
        "Track Solana transaction fees in real-time. SOL fees are typically $0.00025 per transaction — see current rates and historical trends.",
        "solana fee tracker, sol transaction fees, solana gas fees, solana vs ethereum cost",
        "solana"
    ),
    (
        "gas-fee-comparison",
        "Gas Fee Comparison — 25+ Blockchains Compared | FeeScout",
        "Compare gas fees across 25+ blockchains. See which chains are cheapest for transactions, DeFi, NFTs, and bridging.",
        "gas fee comparison, blockchain fees compared, cheapest L2, ethereum vs polygon fees, crypto transaction cost",
        "comparison"
    ),
    (
        "best-time-to-buy-crypto",
        "Best Time to Buy Crypto — Gas Fee Timing Guide | FeeScout",
        "Discover the cheapest times to transact on every major blockchain. Our data shows exactly when gas fees are lowest.",
        "best time to buy crypto, cheapest gas fees, when to transact crypto, crypto transaction timing",
        "guide"
    ),
    (
        "nft-gas-fees",
        "NFT Gas Fees — How to Save on Minting & Trading | FeeScout",
        "NFT gas fees can eat your profits. Learn how to time your mints, trades, and transfers to save 50-80% on gas.",
        "nft gas fees, nft minting cost, opensea gas fees, nft trading costs, cheap nft transactions",
        "nft"
    ),
    (
        "defi-gas-optimization",
        "DeFi Gas Optimization — Save $100s on DeFi Transactions | FeeScout",
        "DeFi gas fees can eat 5-15% of your profits. Learn strategies to minimize gas costs across swaps, yield farming, and more.",
        "defi gas fees, defi gas optimization, yield farming gas cost, uniswap gas fees, defi transaction cost",
        "defi"
    ),
    (
        "crypto-gas-fee-api",
        "Crypto Gas Fee API — Real-Time Data for Developers | FeeScout",
        "REST API providing real-time gas fee data across 25+ blockchains. Free tier available. Up to 100K requests/day.",
        "gas fee api, crypto api, ethereum gas api, blockchain data api, gas price api",
        "api"
    ),
]


def generate_seo_page(slug: str, title: str, description: str, keywords: str, template: str) -> str:
    """Generate a complete SEO-optimized HTML page."""
    
    chain_data = {
        "ethereum": {"name": "Ethereum", "symbol": "ETH", "unit": "gwei", "avg_fee": "$2-50"},
        "bitcoin": {"name": "Bitcoin", "symbol": "BTC", "unit": "sat/vB", "avg_fee": "$1-10"},
        "polygon": {"name": "Polygon", "symbol": "MATIC", "unit": "gwei", "avg_fee": "$0.001-0.01"},
        "arbitrum": {"name": "Arbitrum", "symbol": "ARB", "unit": "gwei", "avg_fee": "$0.01-0.10"},
        "solana": {"name": "Solana", "symbol": "SOL", "unit": "lamports", "avg_fee": "$0.00025"},
    }
    
    chain = chain_data.get(template, {"name": "Crypto", "symbol": "CRYPTO", "unit": "gwei", "avg_fee": "Varies"})
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{description}">
    <meta name="keywords" content="{keywords}">
    <link rel="canonical" href="https://feescout.bond/{slug}">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; max-width: 800px; margin: 0 auto; padding: 40px 20px; line-height: 1.8; color: #1a1a2e; }}
        h1 {{ font-size: 36px; margin-bottom: 20px; color: #07070C; }}
        h2 {{ font-size: 24px; margin-top: 40px; margin-bottom: 16px; color: #07070C; }}
        h3 {{ font-size: 20px; margin-top: 24px; }}
        .highlight {{ background: #f0fdf4; padding: 20px; border-radius: 8px; border-left: 4px solid #00D68F; margin: 20px 0; }}
        .cta {{ display: inline-block; background: #00D68F; color: #000; padding: 16px 32px; border-radius: 8px; text-decoration: none; font-weight: 700; margin: 20px 0; }}
        .cta:hover {{ background: #00B87A; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f9fafb; font-weight: 600; }}
        .cheap {{ color: #059669; font-weight: 600; }}
        .expensive {{ color: #dc2626; font-weight: 600; }}
        .faq {{ margin-top: 40px; }}
        .faq-item {{ margin-bottom: 24px; }}
        .faq-item h3 {{ margin-bottom: 8px; }}
        footer {{ margin-top: 60px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px; }}
    </style>
</head>
<body>
    <nav><a href="https://feescout.bond" style="color:#00D68F;text-decoration:none;font-weight:700;">← Back to FeeScout</a></nav>
    
    <h1>{title}</h1>
    
    <p>{description}</p>
    
    <div class="highlight">
        <strong>💡 Quick insight:</strong> {chain['name']} transaction fees average {chain['avg_fee']}. 
        By timing your transactions during low-fee periods, you can save 40-80% on every transaction.
    </div>
    
    <a href="https://feescout.bond" class="cta">Track {chain['name']} Gas Fees Live →</a>
    
    <h2>Current {chain['name']} Gas Prices</h2>
    <p>Gas fees on {chain['name']} are measured in {chain['unit']}. Here's what different fee levels mean:</p>
    
    <table>
        <tr><th>Fee Level</th><th>{chain['unit']}</th><th>Confirmation Time</th><th>Best For</th></tr>
        <tr><td class="cheap">Low</td><td class="cheap">Below average</td><td>5-30 min</td><td>Non-urgent transfers</td></tr>
        <tr><td>Normal</td><td>Average</td><td>1-5 min</td><td>Standard transactions</td></tr>
        <tr><td class="expensive">High</td><td class="expensive">Above average</td><td>&lt;1 min</td><td>Urgent transactions</td></tr>
    </table>
    
    <h2>How to Save on {chain['name']} Gas Fees</h2>
    
    <h3>1. Time Your Transactions</h3>
    <p>Gas fees follow predictable patterns. Weekends are typically 30-50% cheaper than weekdays. Late night (US time) is cheaper than business hours.</p>
    
    <h3>2. Use FeeScout Alerts</h3>
    <p>Instead of manually checking gas prices, set a target fee and let FeeScout notify you when fees drop below your threshold.</p>
    
    <h3>3. Consider Layer 2 Solutions</h3>
    <p>If you're transacting frequently, consider using L2 solutions like Arbitrum, Optimism, or Base for significantly lower fees.</p>
    
    <h2>Track {chain['name']} Fees with FeeScout</h2>
    <p>FeeScout provides real-time {chain['name']} gas fee monitoring with:</p>
    <ul>
        <li>✅ Live fee updates every 60 seconds</li>
        <li>✅ Custom price alerts</li>
        <li>✅ Historical fee data</li>
        <li>✅ REST API for developers</li>
        <li>✅ Free tier available</li>
    </ul>
    
    <a href="https://feescout.bond/#pricing" class="cta">Start Tracking for Free →</a>
    
    <div class="faq">
        <h2>Frequently Asked Questions</h2>
        
        <div class="faq-item">
            <h3>What are {chain['name']} gas fees?</h3>
            <p>Gas fees are transaction costs paid to validators on the {chain['name']} network. They vary based on network demand and transaction complexity.</p>
        </div>
        
        <div class="faq-item">
            <h3>When are {chain['name']} gas fees lowest?</h3>
            <p>Typically during weekends and late-night hours (US time). FeeScout's historical data shows consistent patterns you can use to time transactions.</p>
        </div>
        
        <div class="faq-item">
            <h3>How much can I save with FeeScout?</h3>
            <p>Most active traders save $100-400/month by timing transactions during low-fee periods identified by FeeScout.</p>
        </div>
        
        <div class="faq-item">
            <h3>Does FeeScout support other blockchains?</h3>
            <p>Yes! FeeScout tracks gas fees across 25+ blockchains including Ethereum, Bitcoin, Polygon, Arbitrum, Solana, and many more.</p>
        </div>
    </div>
    
    <footer>
        <p>© 2025 FeeScout. Real-time gas fee data for 25+ blockchains.</p>
        <p><a href="https://feescout.bond">Home</a> | <a href="https://feescout.bond/#pricing">Pricing</a> | <a href="https://feescout.bond/api/docs">API Docs</a></p>
    </footer>
</body>
</html>"""


def generate_all_pages(output_dir: str = "marketing/pages/seo"):
    """Generate all SEO pages."""
    os.makedirs(output_dir, exist_ok=True)
    
    for slug, title, description, keywords, template in SEO_PAGES:
        html = generate_seo_page(slug, title, description, keywords, template)
        filepath = os.path.join(output_dir, f"{slug}.html")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Generated: {filepath}")
    
    print(f"\nGenerated {len(SEO_PAGES)} SEO pages in {output_dir}/")


if __name__ == "__main__":
    generate_all_pages()
