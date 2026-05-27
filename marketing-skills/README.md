# FeeScout Marketing Skills

AI-powered marketing toolkit integrated into FeeScout. Six skill modules covering SEO, content, growth experimentation, conversion optimization, outbound campaigns, and sales pipeline automation.

---

## Included Skills

### seo-ops — AI SEO Ops
Find the keywords your competitors missed. Automatically.

Replaces manual keyword research, competitor analysis, content briefing, and trend detection. Pulls data from Google Search Console, Ahrefs, and the open web to surface high-impact opportunities ranked by confidence and ready to execute.

Key tools:
- **Content Attack Brief Generator** — Synthesizes your content footprint, Ahrefs data, GSC performance, and competitor gaps into a weekly prioritized keyword brief. Scores every keyword on Impact × Confidence.
- **GSC Keyword Optimizer** — Finds "striking distance" keywords (positions 4–20 with decent impressions) for quick page-one wins, CTR underperformers, and traffic gain projections.
- **GSC Client & Auth** — Reusable Google Search Console API client with OAuth flow.

For FeeScout: Identify fee-related search terms competitors rank for, find quick-win content opportunities, and track organic traffic to fee comparison pages.

---

### content-ops — AI Content Ops
Ship content that scores 90+ every time. Automatically.

Scores, gates, and iterates every piece of content through an AI expert panel before it goes live. Nothing ships below 90/100.

Key tools:
- **Expert Panel** — Auto-assembles 7–10 domain experts tailored to whatever you're scoring. Loops until every expert scores 90+. Includes a 1.5x-weighted AI Writing Detector catching all 24 known AI writing patterns.
- **Content Quality Gate** — CI/CD-style gate that filters out drafts below threshold.
- **Content Quality Scorer** — 5-dimension scoring: voice similarity (35%), specificity (25%), AI slop penalty (20%), length appropriateness (10%), engagement potential (10%).
- **Editorial Brain** — Automated editorial strategy and planning.

For FeeScout: Ensure every fee guide, comparison article, and landing page meets expert-level quality standards before publishing.

---

### growth-engine — AI Growth Engine
Autonomous growth experimentation for AI agents.

Creates experiments with hypotheses, collects data, runs statistical analysis (Bootstrap CI + Mann-Whitney U), auto-promotes winners to a living playbook, and suggests what to test next.

Key features:
- **Experiment Engine** — A/B or batch (up to 10 variants) with hypotheses tracking.
- **Auto-Playbook** — Winners automatically promote to a living playbook of empirically proven best practices.
- **Weekly Scorecard** — Automated report across all channels: wins, trends, running experiments, discards.
- **Pacing Alerts** — Monitor campaign health against targets.

For FeeScout: Systematically test messaging, page layouts, and feature positioning to optimize user acquisition and engagement.

---

### conversion-ops — AI Conversion Ops
Turn landing pages into conversion machines. Turn survey data into lead magnets.

Scores landing pages across 8 proven conversion dimensions and transforms raw survey responses into segmented lead magnet strategies — no API keys or headless browsers required.

Key tools:
- **CRO Audit Tool** — Fetches any URL and scores it across 8 dimensions: headlines, CTAs, social proof, form friction, mobile responsiveness, page speed, trust signals, urgency. Generates specific fix recommendations with before/after suggestions.
- **Survey-to-Lead-Magnet Engine** — Ingests survey CSVs, clusters respondents by pain points, ranks segments by commercial potential, and generates complete lead magnet briefs.

For FeeScout: Audit and optimize fee calculator pages, comparison tools, and signup flows. Convert user feedback into targeted lead magnets.

---

### outbound-engine — AI Outbound Engine
From ICP definition to emails in inbox — fully automated cold outbound.

Handles the complete cold outbound pipeline: ICP definition, expert-scored email sequences, lead sourcing and verification, deduplication, platform upload, and competitive monitoring.

Key tools:
- **Cold Outbound Optimizer** — ICP definition, infrastructure audit (Instantly), expert panel scoring (10 simulated outbound experts, recursive until 90+), sequence copywriting, capacity planning, and implementation docs.
- **Lead Pipeline** — Apollo people search, LeadMagic verification, deduplication, batch upload to Instantly with rate limiting.
- **Competitive Monitor** — Pricing page change detection and blog post monitoring.

For FeeScout: Automate outreach to potential partners (financial institutions, affiliate channels) and monitor competitor positioning.

---

### sales-pipeline — AI Sales Pipeline
Turn anonymous website visitors into qualified pipeline in under 60 seconds.

Complete sales pipeline automation: visitor identification through intent scoring, suppression, campaign routing, dead deal resurrection, trigger-based prospecting, and self-learning ICP optimization.

Key tools:
- **RB2B Webhook Ingest** — Intent scoring (pricing=90, blog=30, services=65) + ICP classification from website pixel data.
- **Suppression Pipeline** — 5-layer check: CRM, outbound, Stripe, analytics, blocklist, with company-level deduplication.
- **Dead Deal Resurrection** — Identifies and re-engages stalled opportunities.
- **Trigger-Based Prospecting** — Auto-responds to intent signals.
- **Self-Learning ICP** — Continuously refines ideal customer profile based on conversion data.

For FeeScout: Identify high-intent visitors exploring fee data, suppress existing customers from sales outreach, and auto-route qualified partners to the sales team.
