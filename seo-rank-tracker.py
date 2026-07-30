#!/usr/bin/env python3
"""
FeeScout SEO Ranking Tracker
Tracks keyword rankings using free Google search (no API key needed).
Stores results in a local CSV for trend analysis.

Usage:
    python seo_rank_tracker.py

Requirements:
    pip install requests beautifulsoup4

Schedule: Run daily via cron or Windows Task Scheduler
"""

import csv
import json
import os
import time
import random
import datetime
import argparse
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Install dependencies: pip install requests beautifulsoup4")
    raise

# ─── Configuration ───────────────────────────────────────────────────────────

DOMAIN = "feescout.bond"
DATA_DIR = Path(__file__).parent / "seo-data"
RANKINGS_CSV = DATA_DIR / "rankings.csv"
KEYWORDS_FILE = DATA_DIR / "keywords.json"

# Keywords to track — update these based on your target terms
DEFAULT_KEYWORDS = [
    "crypto gas fee tracker",
    "ethereum gas fee monitor",
    "blockchain transaction fee api",
    "cheapest crypto chain to transact",
    "gas fee comparison tool",
    "real time gas fees",
    "crypto gas price api",
    "ethereum layer 2 gas comparison",
    "polygon vs ethereum gas fees",
    "arbitrum gas fee tracker",
    "solana transaction fee",
    "base chain gas fees",
    "optimism gas cost",
    "bnb chain transaction fee",
    "crypto fee savings tool",
]

# ─── Functions ───────────────────────────────────────────────────────────────

def ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)
    if not KEYWORDS_FILE.exists():
        KEYWORDS_FILE.write_text(json.dumps(DEFAULT_KEYWORDS, indent=2))
        print(f"Created keywords file: {KEYWORDS_FILE}")
    if not RANKINGS_CSV.exists():
        RANKINGS_CSV.write_text("date,keyword,position,page,result_url,result_title\n")
        print(f"Created rankings file: {RANKINGS_CSV}")

def load_keywords():
    return json.loads(KEYWORDS_FILE.read_text())

def search_google(query, num_results=30):
    """
    Search Google and return results. Uses a realistic User-Agent.
    NOTE: Google may rate-limit or block automated queries.
    For production use, consider SerpAPI or similar paid service.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }
    
    url = "https://www.google.com/search"
    params = {
        "q": query,
        "num": num_results,
        "hl": "en",
        "gl": "us",
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"  [WARN] Search failed for '{query}': {e}")
        return None

def parse_results(html):
    """Parse Google search results HTML and return list of {url, title} dicts."""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    
    # Google's result containers
    for div in soup.select("div.g"):
        a = div.select_one("a")
        title_el = div.select_one("h3")
        if a and title_el:
            href = a.get("href", "")
            if href.startswith("http"):
                results.append({
                    "url": href,
                    "title": title_el.get_text(strip=True),
                })
    
    return results

def find_domain_position(results, domain):
    """Find the position of our domain in search results. Returns (position, url, title) or None."""
    for i, result in enumerate(results, 1):
        if domain in result["url"]:
            return (i, result["url"], result["title"])
    return None

def track_keyword(keyword):
    """Track a single keyword. Returns dict with results."""
    html = search_google(keyword)
    if not html:
        return {"keyword": keyword, "position": None, "page": None, "url": "", "title": "", "error": "search_failed"}
    
    results = parse_results(html)
    found = find_domain_position(results, DOMAIN)
    
    if found:
        pos, url, title = found
        page = (pos - 1) // 10 + 1
        return {
            "keyword": keyword,
            "position": pos,
            "page": page,
            "url": url,
            "title": title,
            "error": None,
        }
    else:
        return {
            "keyword": keyword,
            "position": None,
            "page": None,
            "url": "",
            "title": "",
            "error": None,
        }

def save_result(result, date_str):
    """Append a result to the CSV."""
    with open(RANKINGS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            date_str,
            result["keyword"],
            result["position"] if result["position"] else "not_found",
            result["page"] if result["page"] else "",
            result["url"],
            result["title"],
        ])

def print_report(date_str):
    """Print a summary report of today's rankings."""
    if not RANKINGS_CSV.exists():
        print("No data yet.")
        return
    
    today_rows = []
    with open(RANKINGS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["date"] == date_str:
                today_rows.append(row)
    
    if not today_rows:
        print(f"No data for {date_str}")
        return
    
    print(f"\n{'='*70}")
    print(f"  FeeScout SEO Ranking Report — {date_str}")
    print(f"{'='*70}")
    
    found = [r for r in today_rows if r["position"] != "not_found"]
    not_found = [r for r in today_rows if r["position"] == "not_found"]
    
    print(f"\n  Tracked: {len(today_rows)} keywords")
    print(f"  Ranking: {len(found)}")
    print(f"  Not found: {len(not_found)}")
    
    if found:
        print(f"\n  {'Keyword':<40} {'Pos':>4} {'Page':>5}")
        print(f"  {'-'*40} {'-'*4} {'-'*5}")
        for r in sorted(found, key=lambda x: int(x["position"])):
            print(f"  {r['keyword']:<40} {r['position']:>4} {r['page']:>5}")
    
    if not_found:
        print(f"\n  Not ranking:")
        for r in not_found:
            print(f"    - {r['keyword']}")
    
    print(f"\n{'='*70}\n")

def show_trends(days=14):
    """Show ranking trends over the last N days."""
    if not RANKINGS_CSV.exists():
        print("No data yet.")
        return
    
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    
    rows = []
    with open(RANKINGS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["date"] >= cutoff:
                rows.append(row)
    
    if not rows:
        print(f"No data in the last {days} days.")
        return
    
    # Group by keyword
    keywords = {}
    for row in rows:
        kw = row["keyword"]
        if kw not in keywords:
            keywords[kw] = []
        keywords[kw].append(row)
    
    print(f"\n{'='*70}")
    print(f"  FeeScout SEO Trends — Last {days} days")
    print(f"{'='*70}\n")
    
    for kw, data in keywords.items():
        positions = []
        for r in data:
            if r["position"] != "not_found":
                positions.append(int(r["position"]))
        
        if positions:
            latest = positions[-1]
            avg = sum(positions) / len(positions)
            best = min(positions)
            trend = ""
            if len(positions) >= 2:
                diff = positions[-1] - positions[0]
                trend = f" ({'↑' if diff < 0 else '↓' if diff > 0 else '→'} {abs(diff)})"
            print(f"  {kw:<40} latest: {latest:>3}  avg: {avg:>5.1f}  best: {best:>3}{trend}")
        else:
            print(f"  {kw:<40} not ranking")
    
    print()

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FeeScout SEO Ranking Tracker")
    parser.add_argument("--report", action="store_true", help="Show today's report")
    parser.add_argument("--trends", action="store_true", help="Show trends")
    parser.add_argument("--days", type=int, default=14, help="Days for trends")
    parser.add_argument("--keyword", type=str, help="Track a single keyword")
    args = parser.parse_args()
    
    ensure_data_dir()
    date_str = datetime.date.today().isoformat()
    
    if args.report:
        print_report(date_str)
        return
    
    if args.trends:
        show_trends(args.days)
        return
    
    if args.keyword:
        print(f"Tracking: {args.keyword}")
        result = track_keyword(args.keyword)
        save_result(result, date_str)
        if result["position"]:
            print(f"  Position: {result['position']} (page {result['page']})")
            print(f"  URL: {result['url']}")
        else:
            print("  Not found in top 30 results")
        return
    
    # Default: track all keywords
    keywords = load_keywords()
    print(f"Tracking {len(keywords)} keywords for {DOMAIN}...")
    print(f"Date: {date_str}\n")
    
    for i, keyword in enumerate(keywords, 1):
        print(f"  [{i}/{len(keywords)}] {keyword}...")
        result = track_keyword(keyword)
        save_result(result, date_str)
        
        if result["position"]:
            print(f"    -> Position {result['position']} (page {result['page']})")
        elif result["error"]:
            print(f"    -> ERROR: {result['error']}")
        else:
            print(f"    -> Not in top 30")
        
        # Be polite — random delay between requests
        if i < len(keywords):
            delay = random.uniform(3, 7)
            time.sleep(delay)
    
    print(f"\nDone. Results saved to {RANKINGS_CSV}")
    print_report(date_str)

if __name__ == "__main__":
    main()
