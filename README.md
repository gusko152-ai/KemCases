# KemCases

Telegram bot + Telegram Mini App starter for a Standoff 2 gold rewards community.

## Included
- Telegram bot menu: balance, reward history, referrals and withdrawal requests.
- Admin review flow for withdrawal requests.
- PostgreSQL-ready database (SQLite is supported for local development).
- Mini App shell for the rewarded-ad provider integration.
- Server-side signed callback endpoint with idempotency protection.

## Important
Rewarded ads are **disabled by default**. Do not credit balances from a button click or a client-side event. Connect an ad network that explicitly permits incentivized traffic and virtual-currency rewards, then implement its server-to-server verification in `app/ads.py`. Confirm Standoff 2 rules and the provider's terms before launch. This project does not generate advertising revenue by itself.

## Run locally
1. Copy `.env.example` to `.env` and set `BOT_TOKEN`.
2. Install: `pip install -r requirements.txt`
3. Run: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

The bot starts polling when the application starts. Set `ADMIN_IDS` to comma-separated Telegram numeric IDs.

## Deploy
See [docs/DEPLOY.md](docs/DEPLOY.md). Use managed PostgreSQL in production; Render's local filesystem is ephemeral on the free service tier.
