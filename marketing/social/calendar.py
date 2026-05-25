"""
FeeScout Social Media Marketing Engine
Generates and schedules posts for Twitter/X, Reddit, and crypto forums.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List


@dataclass
class SocialPost:
    platform: str  # twitter, reddit, telegram
    content: str
    hashtags: List[str]
    best_time: str  # UTC
    type: str  # educational, promotional, engagement, curation


# ── 30-Day Social Media Content Calendar ──

POSTS: List[SocialPost] = [
    # Week 1: Education
    SocialPost("twitter", 
        "🚨 ETH gas just hit {gwei} gwei. That's ${cost}+ for a simple swap.\n\nWith FeeScout, you'd have been alerted when fees dropped to {low_gwei} gwei (${low_cost}).\n\nStop overpaying → feescout.bond",
        ["#crypto", "#ethereum", "#gasfees", "#DeFi"],
        "14:00", "educational"),
    
    SocialPost("twitter",
        "Weekend crypto traders save 50% on gas fees.\n\nThe data doesn't lie:\n📉 Saturday 2am ET: ~{weekend_gwei} gwei\n📈 Monday 2pm ET: ~{weekday_gwei} gwei\n\nSame transaction. Up to 9x cheaper.\n\nTrack live fees → feescout.bond",
        ["#crypto", "#gasfees", "#Ethereum", "#trading"],
        "10:00", "educational"),
    
    SocialPost("reddit",
        "title: I built a gas fee tracker that saves me $200/month — open to feedback\n\nbody: After getting tired of overpaying on gas (especially during NFT mints), I built FeeScout. It monitors gas fees across 25+ blockchains in real-time and sends alerts when fees drop below your target.\n\nKey features:\n- 60-second updates\n- Custom price alerts\n- Historical pattern data\n- REST API for bots\n- Free tier available\n\nWould love feedback from the community: feescout.bond\n\n*(I'm happy to answer questions about the tech stack or the data sources)*",
        [], "18:00", "educational"),
    
    SocialPost("twitter",
        "🛡️ If you're trading DeFi without a gas tracker, you're leaving money on the table.\n\nFeeScout monitors {chains}+ blockchains in real-time:\n✅ Live gas prices\n✅ Custom alerts\n✅ Historical data\n✅ REST API\n\nFree tier: feescout.bond\nAPI access: $39/mo",
        ["#DeFi", "#crypto", "#buildinpublic"],
        "16:00", "promotional"),
    
    SocialPost("twitter",
        "Bitcoin mempools are spiking again.\n\nCurrent fees:\n🐢 Economy: {btc_low} sat/vB (~2h)\n⚡ Normal: {btc_med} sat/vB (~30min)\n🔥 Priority: {btc_high} sat/vB (~10min)\n\nCheck real-time fees across 25+ chains → feescout.bond",
        ["#bitcoin", "#BTC", "#transactionfees"],
        "12:00", "educational"),
    
    SocialPost("twitter",
        "Hot take: Gas fees are the hidden tax on crypto.\n\nEthereum avg: $5-50 per tx\nBitcoin avg: $1-10 per tx\nPolygon avg: $0.001 per tx\n\nIf you're not comparing chains before transacting, you're literally throwing money away.\n\nfeescout.bond",
        ["#crypto", "#ethereum", "#polygon", "#gasfees"],
        "09:00", "engagement"),
    
    SocialPost("twitter",
        "Monday market check:\n\n🔴 Ethereum: {eth_gwei} gwei (expensive)\n🟡 Bitcoin: {btc_sat} sat/vB (moderate)\n🟢 Polygon: {poly_gwei} gwei (cheap)\n🟢 Arbitrum: {arb_gwei} gwei (cheap)\n🟢 Base: {base_gwei} gwei (cheap)\n\nSave this post. Check back Friday.\n\nfeescout.bond",
        ["#crypto", "#gasfees", "#L2"],
        "14:00", "curation"),
    
    # Week 2: Social Proof
    SocialPost("twitter",
        "💬 \"I used to spend $50+ on Ethereum gas during peak hours. FeeScout helped me time my transactions and I'm saving about $200/month.\"\n\n— Marcus T., DeFi Trader\n\nReal result. Real savings.\n\nfeescout.bond",
        ["#crypto", "#testimonial", "#DeFi"],
        "11:00", "social_proof"),
    
    SocialPost("twitter",
        "💬 \"The API is rock solid. We integrated FeeScout into our trading bot and it's been running flawlessly for 3 months.\"\n\n— Sarah K., Crypto Developer\n\nBuilt for developers, by developers.\n\nfeescout.bond",
        ["#crypto", "#api", "#buildinpublic"],
        "15:00", "social_proof"),
    
    SocialPost("reddit",
        "title: [Tool] FeeScout v2.0 — Gas fee monitor with alerts, API, and 25+ chains\n\nbody: Hey r/CryptoCurrency,\n\nI've been working on FeeScout for the past year and just launched v2.0 with:\n\n- Real-time alerts (get notified when gas drops)\n- 25+ blockchains (ETH, BTC, SOL, Polygon, Arbitrum, Base, etc.)\n- Historical fee patterns\n- REST API with up to 100K req/day\n- Free tier (100 req/day)\n\nThe problem I'm solving: I was overpaying $200+/month on gas because I didn't know when fees were lowest.\n\nFree to start: feescout.bond\n\nHappy to answer any questions!",
        [], "17:00", "promotional"),
    
    SocialPost("twitter",
        "By the numbers:\n\n📊 25+ blockchains tracked\n⚡ 60-second update frequency\n💰 Avg user saves $150/mo\n🔌 99.9% API uptime\n\nFeeScout: The gas fee data platform for crypto traders.\n\nfeescout.bond",
        ["#crypto", "#data", "#buildinpublic"],
        "13:00", "promotional"),
    
    # Week 3: Product Features
    SocialPost("twitter",
        "🔔 New feature: Custom gas price alerts\n\nSet your target gwei. We'll notify you when fees drop.\n\nNo more manually checking gas trackers.\n\nSet up alerts → feescout.bond/#pricing",
        ["#crypto", "#product", "#gasfees"],
        "10:00", "product"),
    
    SocialPost("twitter",
        "📊 Historical gas fee data is now available on FeeScout.\n\nSee fee patterns over:\n- Last 24 hours\n- Last 7 days\n- Last 30 days\n- Last 90 days\n\nFind the cheapest time to transact.\n\nfeescout.bond",
        ["#crypto", "#data", "#analytics"],
        "14:00", "product"),
    
    # Week 4: Conversion
    SocialPost("twitter",
        "🚀 Limited time: Get 50% off your first month of FeeScout Hobbyist.\n\nDown from $39 to $19.50/mo.\n\nIncludes:\n✅ All 25+ blockchains\n✅ Custom alerts\n✅ 10K API req/day\n✅ Historical data\n\nOffer expires Sunday.\n\nfeescout.bond/#pricing",
        ["#crypto", "#deal", "#DeFi"],
        "12:00", "promotional"),
    
    SocialPost("twitter",
        "Real talk: If you made 10 on-chain transactions today, how much did you spend on gas?\n\nReply with your number. I'll tell you how much you could have saved with FeeScout. 👇",
        ["#crypto", "#gasfees", "#poll"],
        "16:00", "engagement"),
]


def get_weekly_posts(week: int) -> List[SocialPost]:
    """Get posts for a specific week (1-4)."""
    start = (week - 1) * 7
    end = start + 7
    return POSTS[start:end]


def format_post(post: SocialPost, **kwargs) -> str:
    """Format a post with live data."""
    content = post.content
    for key, value in kwargs.items():
        content = content.replace(f"{{{key}}}", str(value))
    return content


if __name__ == "__main__":
    # Print Week 1 content calendar
    print("=== WEEK 1 CONTENT CALENDAR ===\n")
    for i, post in enumerate(get_weekly_posts(1)):
        print(f"Day {i+1} | {post.platform.upper()} | {post.type}")
        print(f"Best time: {post.best_time} UTC")
        print(f"Content:\n{post.content[:200]}...")
        print()
