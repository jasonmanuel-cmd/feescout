# FeeScout SEO Monitoring Setup

**Last updated:** 2026-06-10
**Site:** https://feescout.bond

---

## What's Set Up

### 1. Sitemap & Crawl
- `sitemap.xml` — lists all public pages, served at /sitemap.xml
- `robots.txt` — allows all crawlers, blocks /api/ and /dashboard
- Both configured in vercel.json routes

### 2. On-Page SEO (index.html)
- Open Graph tags (og:title, og:description, og:url, og:image)
- Twitter Card meta tags
- JSON-LD structured data (SoftwareApplication schema with pricing)
- GSC verification meta tag placeholder (commented out — needs code)

### 3. Analytics (Ready to Activate)
Plausive analytics script is pre-configured but commented out.
Plausible is privacy-friendly (no cookie banner needed, GDPR compliant).

### 4. Ranking Tracker
`seo-rank-tracker.py` — tracks keyword positions in Google search results.
Stores data in `seo-data/rankings.csv` for trend analysis.

---

## Setup Checklist (Action Required)

### Google Search Console
- [ ] Go to https://search.google.com/search-console
- [ ] Add property: `https://feescout.bond`
- [ ] Choose verification method:
  - **Option A (recommended):** HTML file upload — download the verification HTML file from GSC, place it in the FeeScout root, add route to vercel.json, deploy
  - **Option B:** DNS TXT record — add the TXT record at your domain registrar (.bond)
  - **Option C:** Meta tag — uncomment the google-site-verification meta tag in index.html and paste your code
- [ ] Submit sitemap: `https://feescout.bond/sitemap.xml`
- [ ] Request indexing for key pages

### Analytics (Plausible)
- [ ] Create free account at https://plausible.io
- [ ] Add site: `feescout.bond`
- [ ] Uncomment the Plausible script tag in index.html
- [ ] Deploy to Vercel
- [ ] Verify data is flowing in Plausible dashboard

### Bing Webmaster Tools
- [ ] Go to https://www.bing.com/webmasters
- [ ] Add site: `feescout.bond`
- [ ] Verify (can import from GSC or use meta tag)
- [ ] Submit sitemap

---

## Ranking Tracker Usage

### Install dependencies
```bash
pip install requests beautifulsoup4
```

### Track all keywords
```bash
python seo-rank-tracker.py
```

### Track single keyword
```bash
python seo-rank-tracker.py --keyword "crypto gas fee tracker"
```

### View today's report
```bash
python seo-rank-tracker.py --report
```

### View trends (last 14 days)
```bash
python seo-rank-tracker.py --trends
```

### Custom trend window
```bash
python seo-rank-tracker.py --trends --days 30
```

### Customize keywords
Edit `seo-data/keywords.json` — add/remove target keywords.

### Schedule daily runs
**Windows Task Scheduler:**
1. Open Task Scheduler
2. Create Basic Task → Daily
3. Action: Start a program
4. Program: `python`
5. Arguments: `C:\Users\blunt\Desktop\apps\feescout\seo-rank-tracker.py`
6. Start in: `C:\Users\blunt\Desktop\apps\feescout`

**Or with cron (WSL/Git Bash):**
```bash
# Run daily at 9 AM
0 9 * * * cd /c/Users/blunt/Desktop/apps/feescout && python seo-rank-tracker.py
```

---

## Target Keywords

Currently tracking 15 keywords in `seo-data/keywords.json`:

| Keyword | Intent |
|---------|--------|
| crypto gas fee tracker | TOFU |
| ethereum gas fee monitor | TOFU |
| blockchain transaction fee api | BOFU |
| cheapest crypto chain to transact | MOFU |
| gas fee comparison tool | MOFU |
| real time gas fees | TOFU |
| crypto gas price api | BOFU |
| ethereum layer 2 gas comparison | MOFU |
| polygon vs ethereum gas fees | MOFU |
| arbitrum gas fee tracker | TOFU |
| solana transaction fee | TOFU |
| base chain gas fees | TOFU |
| optimism gas cost | TOFU |
| bnb chain transaction fee | TOFU |
| crypto fee savings tool | BOFU |

---

## Weekly SEO Routine

1. **Monday:** Run ranking tracker, review position changes
2. **Wednesday:** Check GSC for new queries, crawl errors, indexing issues
3. **Friday:** Review analytics (Plausible) — traffic sources, top pages, bounce rate
4. **Monthly:** Review and update target keywords, check competitor rankings

---

## Notes

- Google may rate-limit automated search queries. If the tracker gets blocked,
  consider upgrading to SerpAPI (serpapi.com) for reliable results.
- The ranking tracker uses free Google search — results may vary slightly from
  actual personalized rankings.
- For the 11 SEO content pages (blog/articles), add them to sitemap.xml and
  keywords.json once they're deployed.
