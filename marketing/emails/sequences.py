"""
FeeScout Email Marketing Automation
Uses Resend API (already configured in FeeScout) to send automated email sequences.
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "FeeScout <onboarding@feescout.com>")
API_BASE = "https://api.resend.com"


class EmailSequence:
    """Automated email sequences for FeeScout."""
    
    @staticmethod
    def welcome_email(name: str, dashboard_url: str = "https://feescout.bond/dashboard") -> Dict[str, Any]:
        return {
            "from": RESEND_FROM,
            "subject": "Welcome to FeeScout — Your gas fee savings start now 🚀",
            "html": f"""
            <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:40px 20px;">
                <h1 style="color:#00D68F;">Welcome to FeeScout!</h1>
                <p>Hey {name or 'there'},</p>
                <p>You're now part of a community of crypto traders who refuse to overpay on gas fees.</p>
                <h3>Here's what to do right now:</h3>
                <ol>
                    <li><a href="https://feescout.bond" style="color:#00D68F;">Check live gas fees</a> — see current prices across 25+ chains</li>
                    <li><a href="{dashboard_url}" style="color:#00D68F;">Set up your first alert</a> — get notified when fees drop</li>
                    <li><a href="https://feescout.bond/api/docs" style="color:#00D68F;">Explore the API</a> — integrate gas data into your tools</li>
                </ol>
                <div style="background:#f0f9ff;padding:16px;border-radius:8px;border-left:4px solid #00D68F;margin:20px 0;">
                    <strong>💡 Pro tip:</strong> Gas fees are typically 30-50% lower on weekends. If you're not in a rush, wait until Saturday morning to transact.
                </div>
                <a href="https://feescout.bond" style="display:inline-block;background:#00D68F;color:#000;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:700;margin:16px 0;">Start Tracking →</a>
                <p style="color:#8A8A9A;font-size:14px;">Happy saving,<br>The FeeScout Team</p>
            </div>
            """,
        }
    
    @staticmethod
    def upgrade_email(name: str) -> Dict[str, Any]:
        return {
            "from": RESEND_FROM,
            "subject": "You've checked gas fees 47 times. Let us do the work.",
            "html": f"""
            <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:40px 20px;">
                <h1 style="color:#00D68F;">Stop Checking Gas Fees Manually</h1>
                <p>Hey {name or 'there'},</p>
                <p>I noticed you've been checking gas fees regularly. That's great — you're already saving money. But what if you didn't have to check at all?</p>
                <div style="background:#111118;border:1px solid #1A1A26;border-radius:12px;padding:24px;margin:20px 0;color:#fff;">
                    <h2 style="color:#00D68F;margin-top:0;">FeeScout Hobbyist — $39/mo</h2>
                    <ul style="color:#8A8A9A;line-height:2;">
                        <li>✅ Custom gas price alerts (we notify YOU)</li>
                        <li>✅ All 25+ blockchains (not just 5)</li>
                        <li>✅ 10,000 API requests/day</li>
                        <li>✅ Historical fee data (30 days)</li>
                        <li>✅ Priority email support</li>
                    </ul>
                    <a href="https://square.link/u/YjHtGg2s" style="display:inline-block;background:#00D68F;color:#000;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:700;">Start 7-Day Free Trial →</a>
                </div>
                <p>Most users save $100+/month in gas fees. That's 2.5x the cost of the plan.</p>
                <p style="color:#8A8A9A;font-size:14px;">— The FeeScout Team</p>
            </div>
            """,
        }
    
    @staticmethod
    def trial_expiring_email(name: str, days_left: int) -> Dict[str, Any]:
        return {
            "from": RESEND_FROM,
            "subject": f"Your free trial expires in {days_left} days",
            "html": f"""
            <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:40px 20px;">
                <h1 style="color:#F59E0B;">Your Trial Expires in {days_left} Days</h1>
                <p>Hey {name or 'there'},</p>
                <p>Your FeeScout Hobbyist trial ends soon. Don't lose access to:</p>
                <ul>
                    <li>Real-time gas alerts across 25+ chains</li>
                    <li>10,000 API requests/day</li>
                    <li>Historical fee data</li>
                    <li>Priority support</li>
                </ul>
                <a href="https://square.link/u/YjHtGg2s" style="display:inline-block;background:#00D68F;color:#000;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:700;">Upgrade Now →</a>
                <p style="color:#8A8A9A;font-size:14px;margin-top:24px;">Questions? Just reply to this email.</p>
            </div>
            """,
        }
    
    @staticmethod
    def winback_email(name: str) -> Dict[str, Any]:
        return {
            "from": RESEND_FROM,
            "subject": "We miss you — here's 50% off your first month",
            "html": f"""
            <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:40px 20px;">
                <h1 style="color:#00D68F;">We Miss You, {name or 'Friend'} 💚</h1>
                <p>It's been a while since you used FeeScout. We've been busy improving:</p>
                <ul>
                    <li>🚀 50% faster API responses</li>
                    <li>📊 New historical fee charts</li>
                    <li>🔔 Improved alert system</li>
                    <li>⛓️ 5 new blockchains added</li>
                </ul>
                <p>Come back and get <strong>50% off your first month</strong> of Hobbyist:</p>
                <a href="https://square.link/u/YjHtGg2s?discount=WINBACK50" style="display:inline-block;background:#00D68F;color:#000;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:700;">Claim 50% Off →</a>
                <p style="color:#8A8A9A;font-size:14px;">Offer expires in 7 days.</p>
            </div>
            """,
        }


async def send_email(to: str, email_data: Dict[str, Any]) -> bool:
    """Send an email via Resend API."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — email not sent")
        return False
    
    import httpx
    
    payload = {
        "from": email_data["from"],
        "to": [to],
        "subject": email_data["subject"],
        "html": email_data["html"],
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/emails",
                json=payload,
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            if resp.status_code == 200:
                logger.info(f"Email sent to {to}: {email_data['subject']}")
                return True
            else:
                logger.error(f"Email failed: {resp.status_code} {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Email error: {e}")
        return False


async def send_welcome_sequence(email: str, name: str = ""):
    """Send the welcome email immediately."""
    data = EmailSequence.welcome_email(name)
    return await send_email(email, data)


async def send_upgrade_nudge(email: str, name: str = ""):
    """Send upgrade email to free users."""
    data = EmailSequence.upgrade_email(name)
    return await send_email(email, data)
