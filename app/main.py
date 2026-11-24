import asyncio, json, secrets
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from aiogram import Bot, Dispatcher
from sqlalchemy import select, func
from .config import settings
from .db import init_db, Session
from .models import User, Ledger, Video, WatchSession
from .ads import verify_callback
from .telegram_auth import validate_init_data
from .bot import router
bot=Bot(settings.bot_token)
dp=Dispatcher()
dp.include_router(router)
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task=asyncio.create_task(dp.start_polling(bot))
    yield
    await dp.stop_polling()
    task.cancel()
    await bot.session.close()
app=FastAPI(title="KemCases API",lifespan=lifespan)
@app.get("/health")
async def health(): return {"ok":True,"service":"KemCases"}
@app.get("/app",response_class=HTMLResponse)
async def mini_app():
    from pathlib import Path
    return Path("webapp/index.html").read_text(encoding="utf-8")
def get_webapp_user(request:Request):
    try: return validate_init_data(request.headers.get("X-Telegram-Init-Data",""))
    except ValueError as exc: raise HTTPException(401,str(exc))
@app.get("/api/videos")
async def list_videos(request:Request):
    user=get_webapp_user(request)
    async with Session() as db:
        rows=(await db.execute(select(Video).where(Video.active.is_(True)).order_by(Video.id))).scalars().all()
        completed_ids=(await db.execute(
            select(WatchSession.video_id).where(
                WatchSession.user_id==user["id"],
                WatchSession.rewarded.is_(True)
            )
        )).scalars().all()
        rows=[video for video in rows if video.id not in set(completed_ids)]
        today=datetime.now(timezone.utc).date()
        start=datetime(today.year,today.month,today.day,tzinfo=timezone.utc)
        used=(await db.execute(select(func.count(WatchSession.id)).where(WatchSession.user_id==user["id"],WatchSession.rewarded.is_(True),WatchSession.completed_at>=start))).scalar_one()
    return {"videos":[{"id":v.id,"title":v.title,"url":v.url,"duration":v.duration_seconds,"reward":v.reward} for v in rows],"daily_limit":settings.video_daily_limit,"used_today":used}
@app.post("/api/watch/start")
async def start_watch(request:Request):
    ud=get_webapp_user(request)
    payload=await request.json()
    try: video_id=int(payload.get("video_id"))
    except (ValueError,TypeError): raise HTTPException(400,"Некорректный ID видео")
    async with Session() as db:
        user=await db.get(User,ud["id"])
        if user is None:
            user=User(id=ud["id"],username=ud.get("username")); db.add(user); await db.flush()
        video=await db.get(Video,video_id)
        if not video or not video.active: raise HTTPException(404,"Видео не найдено")
        already_done=(await db.execute(
            select(WatchSession.id).where(
                WatchSession.user_id==user.id,
                WatchSession.video_id==video.id,
                WatchSession.rewarded.is_(True)
            ).limit(1)
        )).scalar_one_or_none()
        if already_done: raise HTTPException(409,"Это задание уже выполнено")
        today=datetime.now(timezone.utc).date()
        start=datetime(today.year,today.month,today.day,tzinfo=timezone.utc)
        used=(await db.execute(select(func.count(WatchSession.id)).where(WatchSession.user_id==user.id,WatchSession.rewarded.is_(True),WatchSession.completed_at>=start))).scalar_one()
        if used>=settings.video_daily_limit: raise HTTPException(429,"Дневной лимит просмотров исчерпан")
        token=secrets.token_urlsafe(32)
        db.add(WatchSession(session_token=token,user_id=user.id,video_id=video.id))
        await db.commit()
        return {"session_token":token,"duration":video.duration_seconds}
@app.post("/api/watch/complete")
async def complete_watch(request:Request):
    ud=get_webapp_user(request); payload=await request.json(); token=payload.get("session_token","")
    async with Session() as db:
        session=(await db.execute(select(WatchSession).where(WatchSession.session_token==token,WatchSession.user_id==ud["id"]))).scalar_one_or_none()
        if not session: raise HTTPException(404,"Сессия просмотра не найдена")
        if session.rewarded: raise HTTPException(409,"За этот просмотр награда уже получена")
        video=await db.get(Video,session.video_id); now=datetime.now(timezone.utc)
        started=session.started_at
        if started.tzinfo is None: started=started.replace(tzinfo=timezone.utc)
        if (now-started).total_seconds()<video.duration_seconds: raise HTTPException(400,"Время просмотра ещё не завершено")
        if not settings.ad_rewards_enabled: raise HTTPException(503,"Начисления отключены до подключения рекламного провайдера")
        user=await db.get(User,session.user_id)
        user.balance+=video.reward; session.rewarded=True; session.completed_at=now
        db.add(Ledger(user_id=user.id,amount=video.reward,reason=f"Просмотр видео №{video.id}"))
        await db.commit()
        return {"ok":True,"reward":video.reward,"balance":user.balance}
@app.post("/webhooks/ads")
async def ad_callback(request:Request):
    if not settings.ad_rewards_enabled: raise HTTPException(503,"Реклама пока не включена")
    raw=await request.body(); signature=request.headers.get("X-Ad-Signature","")
    if not verify_callback(raw,signature): raise HTTPException(401,"Неверная подпись")
    payload=json.loads(raw or b"{}")
    if not payload.get("event_id") or not payload.get("user_id"): raise HTTPException(400,"Не хватает полей события")
    raise HTTPException(501,"Адаптер рекламного провайдера ещё не настроен")
