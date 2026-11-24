# Deploy to Render

1. Create a PostgreSQL database (recommended even for a small production launch).
2. Create a Render Web Service connected to `gusko152-ai/KemCases`.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env.example`. Set `DATABASE_URL` to the PostgreSQL Internal Database URL and `WEBAPP_URL` to the service's public HTTPS URL.
6. Set `ADMIN_IDS` to your Telegram numeric ID. Keep `AD_REWARDS_ENABLED=false` until an eligible ad provider is selected and its server callback is implemented and tested.

The free web service can sleep and its local disk is ephemeral. Do not use local SQLite as the production database.
