from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from sqlalchemy import select, desc
from .config import settings
from .db import Session
from .models import User, Ledger, Withdrawal

router = Router()

def menu():
    rows = [
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
         InlineKeyboardButton(text="📜 История", callback_data="history")],
        [InlineKeyboardButton(text="🎬 Смотреть рекламу", web_app=WebAppInfo(url=settings.webapp_url.rstrip("/") + "/app"))],
        [InlineKeyboardButton(text="👥 Пригласить", callback_data="referral"),
         InlineKeyboardButton(text="💳 Вывод", callback_data="withdraw")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def ensure_user(tg_user, referrer_id=None):
    async with Session() as db:
        user = await db.get(User, tg_user.id)
        if user is None:
            ref = await db.get(User, referrer_id) if referrer_id and referrer_id != tg_user.id else None
            user = User(id=tg_user.id, username=tg_user.username, referred_by=ref.id if ref else None)
            db.add(user)
            await db.commit()
        else:
            user.username = tg_user.username
            await db.commit()
        return user.balance

@router.message(CommandStart())
async def start(message: Message):
    args = (message.text or "").split(maxsplit=1)
    ref = None
    if len(args) > 1 and args[1].startswith("ref_") and args[1][4:].isdigit():
        ref = int(args[1][4:])
    await ensure_user(message.from_user, ref)
    await message.answer(
        "Привет! Это KemCases. Здесь можно смотреть видео, следить за балансом, приглашать друзей и отправлять заявки на вывод.\n\n"
        "Начисления за просмотры включим после подключения рекламного провайдера.",
        reply_markup=menu()
    )

@router.callback_query(F.data == "balance")
async def balance(call: CallbackQuery):
    amount = await ensure_user(call.from_user)
    await call.message.answer(f"💰 Твой баланс: <b>{amount}</b> голды.", reply_markup=menu())
    await call.answer()

@router.callback_query(F.data == "history")
async def history(call: CallbackQuery):
    async with Session() as db:
        rows = (await db.execute(select(Ledger).where(Ledger.user_id == call.from_user.id).order_by(desc(Ledger.created_at)).limit(10))).scalars().all()
    if not rows:
        text = "История пока пустая."
    else:
        text = "📜 Последние операции:\n" + "\n".join(f"{'+' if x.amount > 0 else ''}{x.amount} — {x.reason}" for x in rows)
    await call.message.answer(text, reply_markup=menu())
    await call.answer()

@router.callback_query(F.data == "referral")
async def referral(call: CallbackQuery):
    me = await call.bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{call.from_user.id}"
    await call.message.answer(f"👥 Твоя ссылка для приглашений:\n{link}", reply_markup=menu())
    await call.answer()

@router.callback_query(F.data == "withdraw")
async def withdraw_info(call: CallbackQuery):
    await call.message.answer(
        f"💳 Минимальная сумма заявки: {settings.min_withdrawal} голды.\n"
        "Чтобы создать заявку, отправь команду:\n/withdraw СУММА РЕКВИЗИТЫ",
        reply_markup=menu()
    )
    await call.answer()

@router.message(Command("withdraw"))
async def create_withdrawal(message: Message):
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) != 3 or not parts[1].isdigit():
        await message.answer("Формат: /withdraw 100 ваш_ник_или_реквизиты")
        return
    amount, destination = int(parts[1]), parts[2].strip()
    if amount < settings.min_withdrawal:
        await message.answer(f"Минимум для заявки: {settings.min_withdrawal}.")
        return
    async with Session() as db:
        user = await db.get(User, message.from_user.id)
        if not user or user.balance < amount:
            await message.answer("Недостаточно средств на балансе.")
            return
        user.balance -= amount
        req = Withdrawal(user_id=user.id, amount=amount, destination=destination)
        db.add(req)
        db.add(Ledger(user_id=user.id, amount=-amount, reason="Заявка на вывод"))
        await db.commit()
        request_id = req.id
    await message.answer(f"Заявка №{request_id} создана. Баланс временно уменьшен на {amount} голды.")

@router.message(Command("admin"))
async def admin_help(message: Message):
    if message.from_user.id not in settings.admins:
        return
    await message.answer("Админ-команды:\n/requests — ожидающие заявки\n/approve ID — подтвердить выплату\n/reject ID — вернуть сумму пользователю")
    
@router.message(Command("requests"))
async def requests(message: Message):
    if message.from_user.id not in settings.admins:
        return
    async with Session() as db:
        rows = (await db.execute(select(Withdrawal).where(Withdrawal.status == "pending").order_by(Withdrawal.id))).scalars().all()
    if not rows:
        await message.answer("Ожидающих заявок нет.")
        return
    await message.answer("\n".join(f"№{x.id}: user={x.user_id}, {x.amount} голды, реквизиты: {x.destination}" for x in rows))

@router.message(Command("approve"))
async def approve(message: Message):
    if message.from_user.id not in settings.admins:
        return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /approve ID")
        return
    async with Session() as db:
        req = await db.get(Withdrawal, int(parts[1]))
        if not req or req.status != "pending":
            await message.answer("Заявка не найдена или уже обработана.")
            return
        req.status = "approved"
        await db.commit()
    await message.answer(f"Заявка №{req.id} отмечена как выплаченная. Сам перевод нужно выполнить отдельно.")

@router.message(Command("reject"))
async def reject(message: Message):
    if message.from_user.id not in settings.admins:
        return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /reject ID")
        return
    async with Session() as db:
        req = await db.get(Withdrawal, int(parts[1]))
        if not req or req.status != "pending":
            await message.answer("Заявка не найдена или уже обработана.")
            return
        req.status = "rejected"
        user = await db.get(User, req.user_id)
        user.balance += req.amount
        db.add(Ledger(user_id=user.id, amount=req.amount, reason=f"Возврат по заявке №{req.id}"))
        await db.commit()
    await message.answer(f"Заявка №{req.id} отклонена, сумма возвращена.")


@router.message(Command("addvideo"))
async def add_video(message: Message):
    if message.from_user.id not in settings.admins:
        return
    from .models import Video
    parts = (message.text or "").partition(" ")[2].split("|")
    if len(parts) != 4:
        await message.answer("Формат: /addvideo Название | HTTPS-ссылка-на-видео | длительность_сек | награда_G")
        return
    title, url, duration_raw, reward_raw = [x.strip() for x in parts]
    if not url.startswith("https://") or not title or not duration_raw.isdigit() or not reward_raw.isdigit():
        await message.answer("Проверь данные: ссылка должна начинаться с https://, длительность и награда — целые числа.")
        return
    duration, reward = int(duration_raw), int(reward_raw)
    if not 5 <= duration <= 600 or not 1 <= reward <= 10000:
        await message.answer("Длительность: 5–600 секунд. Награда: 1–10000 G.")
        return
    async with Session() as db:
        video = Video(title=title[:120], url=url[:500], duration_seconds=duration, reward=reward, active=True)
        db.add(video)
        await db.commit()
        await db.refresh(video)
        video_id = video.id
    await message.answer(f"Видео №{video_id} добавлено. Сейчас награды за просмотры заблокированы до подключения рекламной сети.")

@router.message(Command("videos"))
async def admin_videos(message: Message):
    if message.from_user.id not in settings.admins:
        return
    from .models import Video
    async with Session() as db:
        rows = (await db.execute(select(Video).order_by(Video.id))).scalars().all()
    if not rows:
        await message.answer("Видео пока не добавлены. Используй /addvideo.")
        return
    await message.answer("\\n".join(f"№{v.id} | {v.title} | {v.duration_seconds} сек. | {v.reward} G | {'активно' if v.active else 'выключено'}" for v in rows))

@router.message(Command("disablevideo"))
async def disable_video(message: Message):
    if message.from_user.id not in settings.admins:
        return
    parts=(message.text or "").split()
    if len(parts)!=2 or not parts[1].isdigit():
        await message.answer("Формат: /disablevideo ID")
        return
    from .models import Video
    async with Session() as db:
        video=await db.get(Video,int(parts[1]))
        if not video:
            await message.answer("Видео не найдено.")
            return
        video.active=False
        await db.commit()
    await message.answer(f"Видео №{video.id} отключено.")
