FEEscout — Product Listing Copy
================================

Use this copy for your website, Product Hunt, SaaS directories, or any
listing where you need to describe FeeScout.


TAGLINE
-------
Find the cheapest chain, every time.


SHORT DESCRIPTION (1-2 sentences)
----------------------------------
FeeScout is a real-time gas fee comparison API for 27+ blockchains. Stop
overpaying on transaction fees — one API call tells you the cheapest chain
right now.


LONG DESCRIPTION
----------------
FeeScout aggregates live transaction fee data across 27+ blockchains —
Bitcoin, Ethereum, Solana, Polygon, Arbitrum, Base, Avalanche, and more —
and serves it through a simple, fast API.

Whether you're a wallet developer, a DeFi protocol, a payment processor,
or just a crypto user who hates overpaying for gas, FeeScout gives you the
data you need to route transactions to the cheapest chain in real time.

No scraping. No guesswork. No stale data. Fees are refreshed every 60
seconds from Blockchair's blockchain data API, so you always have
up-to-date numbers.


KEY FEATURES
------------

  27+ Blockchains
    Bitcoin, Ethereum, Solana, Polygon, Arbitrum, Optimism, Base,
    Avalanche, BNB Chain, Fantom, Cardano, Polkadot, and many more.

  Real-Time Fees
    Data refreshes every 60 seconds. No stale numbers.

  Simple REST API
    One GET request. JSON response. Any language, any platform.

  Rate-Limited Tiers
    Free tier for hobbyists, paid tiers for production apps.

  Savings Calculator
    Compare fees across chains and see exactly how much you save.

  Dashboard
    Web dashboard to manage your account, monitor usage, and rotate
    your API key.


API EXAMPLE
-----------

  curl -H "X-API-Key: fs_your_key_here" \
    https://feescout.com/api/gas-fees/latest

Response:

  {
    "success": true,
    "count": 27,
    "data": [
      {
        "chain": "solana",
        "fee_usd": 0.000250,
        "fee_native": 0.00000100,
        "fee_type": "lamports",
        "timestamp": "2026-05-24T12:00:00Z"
      },
      ...
    ],
    "updated_at": "2026-05-24T12:00:00Z"
  }


PRICING
-------

  Free         100 requests/day     $0/mo
  Hobbyist     10,000 requests/day  $39/mo
  Trader       100,000 requests/day $99/mo

All plans include the full chain list and real-time data. Paid plans are
processed through Square.


USE CASES
---------

  - Wallets: Show users the cheapest chain before they send
  - DeFi protocols: Route transactions to the lowest-fee network
  - Payment processors: Minimize on-chain settlement costs
  - Trading bots: Factor gas costs into arbitrage calculations
  - Portfolio trackers: Display accurate transfer cost estimates
  - DApps: Help users avoid expensive chains during congestion


SUPPORTED CHAINS
----------------

Bitcoin, Bitcoin Cash, Litecoin, Bitcoin SV, Dogecoin, Dash, XRP,
Groestlcoin, Stellar, Monero, Cardano, Zcash, Mixin, Tezos, EOS,
Ethereum, Polygon, Arbitrum, Optimism, Base, Avalanche, Fantom,
BNB Smart Chain, Moonbeam, Cronos, Gnosis, eCash, Solana


LINKS
-----

  Website:     https://feescout.com
  API Docs:    https://feescout.com/docs
  GitHub:      https://github.com/jasonmanuel-cmd/feescout
  Status:      https://feescout.com/status


ABOUT
-----
FeeScout is built and maintained by LAGNAF Network LLC.
