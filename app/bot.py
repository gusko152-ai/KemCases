from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from sqlalchemy import select, desc, func
from .config import settings
from .db import Session
from .models import User, Ledger, Withdrawal, Video

router = Router()


def money(value) -> str:
    """Display balances using two decimal places (G)."""
    return f"{float(value or 0):.2f}"


def main_menu(user_id: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="💰 Заработок голды", callback_data="earnings"),
        ],
        [
            InlineKeyboardButton(text="📦 Кейсы", callback_data="cases"),
            InlineKeyboardButton(text="💳 Вывод", callback_data="withdraw_home"),
        ],
        [InlineKeyboardButton(text="🛟 Поддержка", callback_data="support")],
    ]
    if user_id in settings.admins:
        rows.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_menu(user_id: int) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="⬅️ Главное меню", callback_data="home")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def ensure_user(tg_user, referrer_id=None):
    async with Session() as db:
        user = await db.get(User, tg_user.id)
        if user is None:
            ref = await db.get(User, referrer_id) if referrer_id and referrer_id != tg_user.id else None
            user = User(
                id=tg_user.id,
                username=tg_user.username,
                referred_by=ref.id if ref else None,
            )
            db.add(user)
        else:
            user.username = tg_user.username
        await db.commit()
        return user.balance


async def send_page(call: CallbackQuery, text: str, markup: InlineKeyboardMarkup):
    await call.message.answer(text, reply_markup=markup)
    await call.answer()


@router.message(CommandStart())
async def start(message: Message):
    args = (message.text or "").split(maxsplit=1)
    ref = None
    if len(args) > 1 and args[1].startswith("ref_") and args[1][4:].isdigit():
        ref = int(args[1][4:])
    await ensure_user(message.from_user, ref)
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n\n"
        "Добро пожаловать в KemCases. Здесь можно выполнять задания, "
        "копить голду, открывать кейсы и отправлять заявки на вывод.\n\n"
        "Выбери нужный раздел в меню:",
        reply_markup=main_menu(message.from_user.id),
    )


@router.callback_query(F.data == "home")
async def home(call: CallbackQuery):
    await send_page(
        call,
        "🏠 Главное меню\nВыбери раздел:",
        main_menu(call.from_user.id),
    )


@router.callback_query(F.data == "profile")
async def profile(call: CallbackQuery):
    await ensure_user(call.from_user)
    async with Session() as db:
        user = await db.get(User, call.from_user.id)
        active_withdrawals = (
            await db.execute(
                select(func.count(Withdrawal.id)).where(
                    Withdrawal.user_id == call.from_user.id,
                    Withdrawal.status.in_(["pending", "processing"]),
                )
            )
        ).scalar_one()
    premium_text = "Нет (функция Premium ещё не подключена)"
    # Premium dates will be stored when the premium subscription feature is added.
    text = (
        "👤 ТВОЙ ПРОФИЛЬ\n\n"
        f"Имя: {call.from_user.full_name}\n"
        f"Telegram ID: {call.from_user.id}\n"
        f"Баланс: {money(user.balance)} G\n"
        f"Активные выводы: {'Есть (' + str(active_withdrawals) + ')' if active_withdrawals else 'Нет'}\n"
        f"Premium: {premium_text}"
    )
    await send_page(call, text, back_menu(call.from_user.id))


@router.callback_query(F.data == "earnings")
async def earnings(call: CallbackQuery):
    async with Session() as db:
        tasks = (
            await db.execute(
                select(Video).where(Video.active.is_(True)).order_by(Video.id)
            )
        ).scalars().all()

    lines = ["💰 ЗАРАБОТОК ГОЛДЫ", ""]
    if tasks:
        for index, task in enumerate(tasks, start=1):
            lines.append(
                f"#{index} {task.title}\n"
                f"Длительность: {task.duration_seconds} секунд\n"
                f"Вознаграждение: {money(task.reward)} G"
            )
            lines.append("")
        lines.append("Нажми кнопку ниже, чтобы открыть Mini App и посмотреть доступные задания.")
    else:
        lines.append("Сейчас активных заданий нет. Загляни позже!")

    rows = []
    if settings.webapp_url:
        rows.append([
            InlineKeyboardButton(
                text="🎬 Открыть задания",
                web_app=WebAppInfo(url=settings.webapp_url.rstrip("/") + "/app"),
            )
        ])
    rows.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="home")])
    await send_page(call, "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data == "cases")
async def cases(call: CallbackQuery):
    await send_page(
        call,
        "📦 КЕЙСЫ\n\n"
        "Здесь появится каталог кейсов. В карточке будет название и стоимость в G. "
        "После выбора кейса игрок увидит полный дроп, шансы выпадения и количество кейсов.\n\n"
        "Покупка кейсов и открытие пока находятся на этапе сборки.",
        back_menu(call.from_user.id),
    )


@router.callback_query(F.data == "withdraw_home")
async def withdraw_home(call: CallbackQuery):
    await send_page(
        call,
        "💳 ВЫВОД ГОЛДЫ\n\n"
        "Минимальная сумма: 5 G\n"
        "Максимальная сумма: 50 000 G\n\n"
        "После ввода суммы бот рассчитает стоимость с учётом +20,1%, "
        "покажет случайную инструкционную картинку и попросит скриншот. "
        "Заявка появится у администраторов после отправки скриншота.\n\n"
        "Приём новых заявок подключим следующим этапом.",
        back_menu(call.from_user.id),
    )


@router.callback_query(F.data == "support")
async def support(call: CallbackQuery):
    await send_page(
        call,
        "🛟 ПОДДЕРЖКА\n\n"
        "Здесь можно будет создать обращение и переписываться с администратором. "
        "После закрытия заявки бот уведомит тебя.\n\n"
        "Система обращений сейчас готовится.",
        back_menu(call.from_user.id),
    )


@router.callback_query(F.data == "admin_panel")
async def admin_panel(call: CallbackQuery):
    if call.from_user.id not in settings.admins:
        await call.answer("Нет доступа", show_alert=True)
        return
    rows = [
        [InlineKeyboardButton(text="🎬 Задания", callback_data="admin_tasks")],
        [InlineKeyboardButton(text="💳 Выводы игроков", callback_data="admin_withdrawals")],
        [InlineKeyboardButton(text="📦 Создание кейсов", callback_data="admin_cases")],
        [InlineKeyboardButton(text="🛟 Поддержка", callback_data="admin_support")],
        [InlineKeyboardButton(text="🧩 Администраторы", callback_data="admin_roles")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="home")],
    ]
    await send_page(
        call,
        "⚙️ АДМИН-ПАНЕЛЬ\n\nВыбери раздел управления:",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data == "admin_tasks")
async def admin_tasks(call: CallbackQuery):
    if call.from_user.id not in settings.admins:
        await call.answer("Нет доступа", show_alert=True)
        return
    async with Session() as db:
        tasks = (await db.execute(select(Video).order_by(Video.id))).scalars().all()
    lines = [
        "🎬 УПРАВЛЕНИЕ ЗАДАНИЯМИ",
        "",
        "Сейчас доступно управление видео через команды:",
        "/addvideo Название | HTTPS-ссылка | секунды | награда_G",
        "/videos — список заданий",
        "/disablevideo ID — отключить задание",
        "",
        "Пошаговый конструктор заданий с загрузкой видео/фото, ориентацией и сроком публикации добавим следующим этапом.",
        "",
        f"Всего заданий в базе: {len(tasks)}",
    ]
    await send_page(call, "\n".join(lines), back_menu(call.from_user.id))


@router.callback_query(F.data == "admin_withdrawals")
async def admin_withdrawals(call: CallbackQuery):
    if call.from_user.id not in settings.admins:
        await call.answer("Нет доступа", show_alert=True)
        return
    async with Session() as db:
        rows = (
            await db.execute(
                select(Withdrawal)
                .where(Withdrawal.status.in_(["pending", "processing"]))
                .order_by(Withdrawal.id)
            )
        ).scalars().all()
    if not rows:
        text = "💳 ВЫВОДЫ ИГРОКОВ\n\nАктивных заявок пока нет."
    else:
        text = "💳 ВЫВОДЫ ИГРОКОВ\n\n" + "\n\n".join(
            f"Заявка №{item.id}\n"
            f"Пользователь: {item.user_id}\n"
            f"Сумма: {money(item.amount)} G\n"
            f"Статус: {item.status}"
            for item in rows
        )
        text += "\n\nПросмотр скриншотов и кнопки обработки подключим в следующем этапе."
    await send_page(call, text, back_menu(call.from_user.id))


@router.callback_query(F.data == "admin_cases")
async def admin_cases(call: CallbackQuery):
    if call.from_user.id not in settings.admins:
        await call.answer("Нет доступа", show_alert=True)
        return
    await send_page(
        call,
        "📦 СОЗДАНИЕ КЕЙСОВ\n\n"
        "Здесь будет пошаговый конструктор: название, цена в G, список предметов, "
        "шансы выпадения и стоимость продажи каждого предмета.",
        back_menu(call.from_user.id),
    )


@router.callback_query(F.data == "admin_support")
async def admin_support(call: CallbackQuery):
    if call.from_user.id not in settings.admins:
        await call.answer("Нет доступа", show_alert=True)
        return
    await send_page(
        call,
        "🛟 ОБРАЩЕНИЯ ИГРОКОВ\n\n"
        "Здесь появится список открытых обращений, переписка с игроком и кнопка закрытия заявки.",
        back_menu(call.from_user.id),
    )


@router.callback_query(F.data == "admin_roles")
async def admin_roles(call: CallbackQuery):
    if call.from_user.id not in settings.admins:
        await call.answer("Нет доступа", show_alert=True)
        return
    await send_page(
        call,
        "🧩 УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ\n\n"
        "/gitadmin USER_ID — добавить администратора\n"
        "/unadmin USER_ID — снять администратора\n\n"
        "Гибкие разрешения для дополнительных администраторов будут добавлены отдельно.",
        back_menu(call.from_user.id),
    )


@router.message(Command("admin"))
async def admin_help(message: Message):
    if message.from_user.id not in settings.admins:
        return
    await message.answer(
        "⚙️ Админ-команды:\n"
        "/requests — старый список ожидающих заявок\n"
        "/approve ID — отметить выплату подтверждённой\n"
        "/reject ID — отклонить старую заявку и вернуть сумму\n"
        "/addvideo Название | HTTPS-ссылка | секунды | награда_G — добавить видео\n"
        "/videos — список роликов\n"
        "/disablevideo ID — отключить ролик\n\n"
        "Также открой Админ-панель в главном меню."
    )


@router.message(Command("requests"))
async def requests(message: Message):
    if message.from_user.id not in settings.admins:
        return
    async with Session() as db:
        rows = (
            await db.execute(
                select(Withdrawal)
                .where(Withdrawal.status == "pending")
                .order_by(Withdrawal.id)
            )
        ).scalars().all()
    if not rows:
        await message.answer("Ожидающих заявок нет.")
        return
    await message.answer(
        "\n".join(
            f"№{x.id}: user={x.user_id}, {money(x.amount)} G, данные: {x.destination}"
            for x in rows
        )
    )


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
        user_id = req.user_id
    await message.answer(f"Заявка №{parts[1]} отмечена как подтверждённая.")
    try:
        await message.bot.send_message(user_id, f"✅ Заявка №{parts[1]} подтверждена администратором.")
    except Exception:
        pass


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
        if user:
            user.balance += req.amount
            db.add(Ledger(user_id=user.id, amount=req.amount, reason=f"Возврат по заявке №{req.id}"))
        user_id = req.user_id
        await db.commit()
    await message.answer(f"Заявка №{parts[1]} отклонена, сумма возвращена если она была списана.")
    try:
        await message.bot.send_message(user_id, f"❌ Заявка №{parts[1]} отклонена.")
    except Exception:
        pass


@router.message(Command("addvideo"))
async def add_video(message: Message):
    if message.from_user.id not in settings.admins:
        return
    parts = (message.text or "").partition(" ")[2].split("|")
    if len(parts) != 4:
        await message.answer("Формат: /addvideo Название | HTTPS-ссылка-на-видео | длительность_сек | награда_G")
        return
    title, url, duration_raw, reward_raw = [x.strip() for x in parts]
    if not url.startswith("https://") or not title or not duration_raw.isdigit() or not reward_raw.isdigit():
        await message.answer("Проверь данные: нужна HTTPS-ссылка, длительность и целая награда.")
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
    await message.answer(
        f"Видео №{video_id} добавлено. Начисление наград остаётся выключенным до подключения "
        "проверяемого рекламного провайдера."
    )


@router.message(Command("videos"))
async def admin_videos(message: Message):
    if message.from_user.id not in settings.admins:
        return
    async with Session() as db:
        rows = (await db.execute(select(Video).order_by(Video.id))).scalars().all()
    if not rows:
        await message.answer("Видео пока не добавлены. Используй /addvideo.")
        return
    await message.answer(
        "\n".join(
            f"№{v.id} | {v.title} | {v.duration_seconds} сек. | {money(v.reward)} G | "
            f"{'активно' if v.active else 'выключено'}"
            for v in rows
        )
    )


@router.message(Command("disablevideo"))
async def disable_video(message: Message):
    if message.from_user.id not in settings.admins:
        return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /disablevideo ID")
        return
    async with Session() as db:
        video = await db.get(Video, int(parts[1]))
        if not video:
            await message.answer("Видео не найдено.")
            return
        video.active = False
        await db.commit()
    await message.answer(f"Видео №{video.id} отключено.")
