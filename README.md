# KemCases

Telegram bot + Telegram Mini App prototype for the KemCases project.

## Main menu prototype
- Profile: Telegram name and ID, balance, active withdrawal count, Premium flag placeholder.
- Earn gold: active video tasks are listed in the bot; the Mini App opens the video and a countdown.
- Cases, withdrawals, support and their admin sections have navigation and explanatory screens. Their transaction/workflow logic is not yet implemented.
- Admin menu: video task management and a view of existing withdrawal records.

## Video rewards safety
The Mini App countdown is only a viewing interface. **Rewards are disabled by default** and must not be enabled by setting a flag until a compliant ad provider has been integrated with server-to-server verification. A client-side timer or button is not proof of a paid ad view. This project does not generate advertising revenue by itself.

## Current admin commands
- `/admin` — command guide
- `/addvideo Title | https://...mp4 | duration_seconds | reward_G`
- `/videos`
- `/disablevideo ID`
- `/requests`, `/approve ID`, `/reject ID` — legacy withdrawal-record commands

## Run locally
1. Copy `.env.example` to `.env` and set `BOT_TOKEN`.
2. Install: `pip install -r requirements.txt`
3. Run: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

Set `ADMIN_IDS` to comma-separated Telegram numeric IDs. See [docs/DEPLOY.md](docs/DEPLOY.md) for hosting notes.
