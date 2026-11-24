import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from sqlalchemy import select
from .config import settings
from .db import init_db, Session
from .models import User, Ledger
from .ads import verify_callback
from .bot import router

bot = Bot(settings.bot_token)
dp = Dispatcher()
dp.include_router(router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(dp.start_polling(bot))
    yield
    await dp.stop_polling()
    task.cancel()
    await bot.session.close()

app = FastAPI(title="KemCases API", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"ok": True, "service": "KemCases"}

@app.get("/app", response_class=HTMLResponse)
async def mini_app():
    from pathlib import Path
    return Path("webapp/index.html").read_text(encoding="utf-8")

@app.post("/webhooks/ads")
async def ad_callback(request: Request):
    if not settings.ad_rewards_enabled:
        raise HTTPException(503, "Rewarded ads are not enabled")
    raw = await request.body()
    signature = request.headers.get("X-Ad-Signature", "")
    if not verify_callback(raw, signature):
        raise HTTPException(401, "Invalid signature")
    # Provider-specific event mapping and event-ID idempotency must be added
    # after selecting an ad network. No balance is credited by this generic endpoint.
    payload = json.loads(raw or b"{}")
    if not payload.get("event_id") or not payload.get("user_id"):
        raise HTTPException(400, "Missing provider event fields")
    raise HTTPException(501, "Provider adapter is not configured yet")
