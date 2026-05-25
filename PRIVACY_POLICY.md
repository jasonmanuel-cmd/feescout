PRIVACY POLICY
===============

Last updated: May 24, 2026

LAGNAF Network LLC ("FeeScout," "we," "us," or "our") operates the FeeScout
API and website at https://feescout.com. This Privacy Policy explains how we
collect, use, store, and protect your information when you use our service.

By using FeeScout, you agree to the practices described in this policy.


1. INFORMATION WE COLLECT
-------------------------

Account Information
  - Email address
  - Password (stored as a PBKDF2-hashed value — we never store plaintext
    passwords)
  - API key (generated at signup for authenticating API requests)

Payment Information
  - Payments are processed entirely by Square. We do not collect, store,
    or have access to your credit card number, bank account, or any other
    payment instrument details.
  - We store only the Square customer ID and subscription tier associated
    with your account.

Usage Data
  - API request logs: endpoint accessed, timestamp, and HTTP status code
  - Daily and total request counts (used for rate-limit enforcement)

Technical Data
  - Session cookies (HTTP-only, secure, SameSite=Lax) to keep you logged
    into the dashboard
  - IP addresses may be logged transiently by our hosting provider (Vercel)
    for security and abuse prevention


2. HOW WE USE YOUR INFORMATION
-------------------------------

We use the information we collect to:

  - Provide, operate, and maintain the FeeScout API
  - Authenticate your API requests and enforce rate limits
  - Process and manage your subscription through Square
  - Send transactional emails (welcome email with API key, account notices)
  - Monitor usage patterns to improve service reliability and performance
  - Prevent abuse, fraud, and unauthorized access


3. THIRD-PARTY SERVICES
-----------------------

FeeScout integrates with the following third-party services. Each has its own
privacy policy governing how they handle data:

  - Blockchair (https://blockchair.com) — blockchain fee data provider.
    We query their API to fetch real-time gas fee information. Blockchair
    does not receive any of your personal data from us.

  - Square (https://squareup.com) — payment processing. When you subscribe
    to a paid plan, Square collects your payment information directly.
    Square's privacy policy applies to that data.

  - Resend (https://resend.com) — transactional email delivery. We send
    your email address and API key to Resend only for the purpose of
    delivering welcome and account-related emails.

  - Supabase / PostgreSQL — database hosting. Your account data is stored
    in a managed PostgreSQL database.

  - Vercel (https://vercel.com) — hosting and deployment. Vercel may
    collect transient access logs (IP address, request metadata) as part
    of their hosting infrastructure.


4. DATA STORAGE AND SECURITY
-----------------------------

  - Passwords are hashed using PBKDF2-HMAC-SHA256 with a unique 16-byte
    salt per account and 100,000 iterations. Plaintext passwords are never
    stored.
  - API keys are generated using cryptographically secure random bytes
    (secrets.token_urlsafe).
  - Session tokens are cryptographically random and stored server-side.
    Session cookies are HTTP-only, secure (HTTPS-only), and expire after
    30 days.
  - All data in transit is encrypted via HTTPS/TLS.
  - We do not sell, rent, or trade your personal information to third
    parties.


5. DATA RETENTION
-----------------

  - Account data is retained as long as your account is active.
  - API usage logs are retained for rate-limit enforcement and service
    analytics. We may delete old logs periodically.
  - If you delete your account, we will remove your personal data from
    our database within 30 days, except where retention is required for
    legal or legitimate business purposes (e.g., payment records).
  - You may request account deletion by contacting us at the email
    address below.


6. YOUR RIGHTS
--------------

You have the right to:

  - Access the personal data we hold about you
  - Correct inaccurate data
  - Request deletion of your account and associated data
  - Export your data (contact us)
  - Opt out of non-essential communications (transactional emails related
    to your account are required for service operation)

To exercise any of these rights, contact us at privacy@feescout.com.


7. CHILDREN'S PRIVACY
----------------------

FeeScout is not directed to children under 13. We do not knowingly collect
personal information from children. If we become aware that a child has
provided us with personal information, we will delete it promptly.


8. CHANGES TO THIS POLICY
--------------------------

We may update this Privacy Policy from time to time. When we make material
changes, we will update the "Last updated" date at the top of this page and,
where appropriate, notify you by email. Continued use of FeeScout after
changes constitutes acceptance of the updated policy.


9. CONTACT
----------

If you have questions about this Privacy Policy or your data, contact us at:

  Email: privacy@feescout.com
  Website: https://feescout.com

LAGNAF Network LLC
