# handlers/user.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID, CATALOG, DELIVERY
from db import (
    get_user, upsert_user, log_action,
    create_order, get_user_orders
)
from keyboards import (
    main_kb, catalog_kb, product_kb,
    confirm_order_kb, cancel_kb
)

router = Router()


class RegStates(StatesGroup):
    name = State()
    telegram = State()


class OrderStates(StatesGroup):
    form = State()


def is_registered(user_id: int) -> bool:
    u = get_user(user_id)
    return bool(u and u.get("registered"))


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    uname = message.from_user.username or ""
    upsert_user(uid, username=uname)
    log_action(uid, "start", f"@{uname}")
    user = get_user(uid)
    admin = uid == ADMIN_ID
    if user and user.get("registered"):
        await message.answer(
            f"Снова ты, {user.get('name') or 'клиент'}.\n\n"
            "Каталог — список документов.\n"
            "Мои заказы — история.\n"
            "Профиль — данные.",
            reply_markup=main_kb(is_admin=admin)
        )
    else:
        await message.answer(
            "Спектр.\n\n"
            "Документы. Бумага настоящая. Записи — по договорённости.\n\n"
            "Для работы нужна регистрация.\n"
            "Нажми /reg",
            reply_markup=main_kb(is_admin=admin)
        )


@router.message(Command("reg"))
@router.message(F.text == "Регистрация")
async def reg_start(message: Message, state: FSMContext):
    uid = message.from_user.id
    if is_registered(uid):
        await message.answer("Ты уже зарегистрирован.", reply_markup=main_kb(uid == ADMIN_ID))
        return
    await state.set_state(RegStates.name)
    await message.answer("Введи имя (логин):", reply_markup=cancel_kb())


@router.message(RegStates.name)
async def reg_name(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb(message.from_user.id == ADMIN_ID))
        return
    name = (message.text or "").strip()
    if len(name) < 2 or len(name) > 64:
        await message.answer("Имя: от 2 до 64 символов. Ещё раз:")
        return
    await state.update_data(name=name)
    await state.set_state(RegStates.telegram)
    await message.answer("Telegram username (@username):")


@router.message(RegStates.telegram)
async def reg_telegram(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb(message.from_user.id == ADMIN_ID))
        return
    tg = (message.text or "").strip()
    if not tg.startswith("@"):
        tg = "@" + tg
    if len(tg) < 2 or len(tg) > 64:
        await message.answer("Некорректный username. Ещё раз:")
        return
    data = await state.get_data()
    name = data.get("name", "")
    uid = message.from_user.id
    uname = message.from_user.username or ""
    upsert_user(uid, username=uname, name=name, telegram=tg, registered=1)
    log_action(uid, "register", f"{name} | {tg}")
    await state.clear()
    await message.answer(
        f"Готово.\n\nИмя: {name}\nTelegram: {tg}\n\nМожешь заказывать.",
        reply_markup=main_kb(uid == ADMIN_ID)
    )


@router.message(F.text == "Каталог")
@router.callback_query(F.data == "catalog")
async def show_catalog(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    text = "Каталог документов:"
    kb = catalog_kb()
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb)
        await event.answer()
    else:
        if not is_registered(event.from_user.id):
            await event.answer("Сначала регистрация: /reg")
            return
        await event.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("cat:"))
async def show_product(callback: CallbackQuery):
    pid = callback.data.split(":")[1]
    item = CATALOG.get(pid)
    if not item:
        await callback.answer("Не найдено", show_alert=True)
        return
    text = (
        f"<b>{item['title']}</b>\n\n"
        f"{item['desc']}\n\n"
        f"Цена: <b>{item['price_text']}</b>"
    )
    await callback.message.edit_text(text, reply_markup=product_kb(pid), parse_mode="HTML")
    await callback.answer()


# ── анкета в одном сообщении ────────────────────────────

FORM_HINT = (
    "Заполни одним сообщением (каждая строка — отдельное поле):\n\n"
    "<code>Город\n"
    "Способ (курьер / закладка / почта)\n"
    "Время\n"
    "Комментарий</code>\n\n"
    "Пример:\n"
    "<code>Москва\n"
    "закладка\n"
    "18:00–21:00\n"
    "рядом с метро</code>"
)


@router.callback_query(F.data.startswith("order:"))
async def order_start(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    if not is_registered(uid):
        await callback.answer("Сначала /reg", show_alert=True)
        return
    pid = callback.data.split(":")[1]
    item = CATALOG.get(pid)
    if not item:
        await callback.answer("Не найдено", show_alert=True)
        return
    await state.set_state(OrderStates.form)
    await state.update_data(product_id=pid)
    await callback.message.edit_text(
        f"Заказ: <b>{item['title']}</b>\n"
        f"Цена: {item['price_text']}\n\n"
        f"{FORM_HINT}",
        parse_mode="HTML"
    )
    await callback.answer()


def _parse_form(text: str):
    lines = [ln.strip() for ln in (text or "").strip().splitlines() if ln.strip()]
    if len(lines) < 3:
        return None
    city = lines[0][:100]
    delivery_raw = lines[1].lower()
    # normalize delivery
    delivery = None
    for key, label in DELIVERY.items():
        if key in delivery_raw or label.lower() in delivery_raw:
            delivery = label
            break
    if delivery is None:
        delivery = lines[1][:80]
    delivery_time = lines[2][:120]
    comment = " ".join(lines[3:])[:500] if len(lines) > 3 else ""
    return city, delivery, delivery_time, comment


@router.message(OrderStates.form)
async def order_form(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb(message.from_user.id == ADMIN_ID))
        return

    parsed = _parse_form(message.text or "")
    if not parsed:
        await message.answer(
            "Нужно минимум 3 строки: город, способ, время.\n\n" + FORM_HINT,
            parse_mode="HTML"
        )
        return

    city, delivery, delivery_time, comment = parsed
    await state.update_data(
        city=city,
        delivery=delivery,
        delivery_time=delivery_time,
        comment=comment,
    )
    data = await state.get_data()
    pid = data.get("product_id")
    item = CATALOG.get(pid)
    if not item:
        await state.clear()
        await message.answer("Ошибка. Начни заново.")
        return

    text = (
        f"<b>Проверь заказ</b>\n\n"
        f"Товар: {item['title']}\n"
        f"Цена: {item['price_text']}\n"
        f"Город: {city}\n"
        f"Получение: {delivery}\n"
        f"Время: {delivery_time}\n"
        f"Комментарий: {comment or '—'}\n\n"
        f"Всё верно?"
    )
    await message.answer(text, reply_markup=confirm_order_kb(), parse_mode="HTML")


@router.callback_query(F.data == "confirm_order")
async def order_confirm(callback: CallbackQuery, state: FSMContext, bot):
    uid = callback.from_user.id
    user = get_user(uid)
    if not user or not user.get("registered"):
        await callback.answer("Сначала /reg", show_alert=True)
        return
    data = await state.get_data()
    pid = data.get("product_id")
    item = CATALOG.get(pid)
    if not item:
        await state.clear()
        await callback.answer("Ошибка", show_alert=True)
        return
    city = data.get("city", "")
    delivery = data.get("delivery", "")
    delivery_time = data.get("delivery_time", "")
    comment = data.get("comment", "")
    await state.clear()
    order_id = create_order(
        user_id=uid,
        username=callback.from_user.username or "",
        name=user.get("name", ""),
        telegram=user.get("telegram", ""),
        product_id=pid,
        product=item["title"],
        price=item["price"],
        city=city,
        delivery=delivery,
        delivery_time=delivery_time,
        comment=comment,
    )
    log_action(uid, "order_create", f"#{order_id} {item['title']} {city}")
    await callback.message.edit_text(
        f"Заказ #{order_id} оформлен.\n\n"
        f"{item['title']}\n"
        f"{city} · {delivery} · {delivery_time}\n\n"
        "Ожидай ответ."
    )
    await callback.answer()
    from keyboards import admin_order_kb
    admin_text = (
        f"<b>Новый заказ #{order_id}</b>\n\n"
        f"Товар: {item['title']}\n"
        f"Цена: {item['price_text']}\n"
        f"Город: {city}\n"
        f"Получение: {delivery}\n"
        f"Время: {delivery_time}\n"
        f"Комментарий: {comment or '—'}\n\n"
        f"Клиент: {user.get('name', '—')}\n"
        f"Telegram: {user.get('telegram', '—')}\n"
        f"TG ID: <code>{uid}</code>\n"
        f"@{callback.from_user.username or '—'}"
    )
    try:
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                admin_text,
                reply_markup=admin_order_kb(order_id),
                parse_mode="HTML"
            )
    except Exception:
        pass


@router.message(F.text == "Мои заказы")
async def my_orders(message: Message):
    uid = message.from_user.id
    if not is_registered(uid):
        await message.answer("Сначала /reg")
        return
    orders = get_user_orders(uid)
    if not orders:
        await message.answer("Заказов нет.")
        return
    status_map = {"pending": "ожидает", "accepted": "принят", "rejected": "отклонён"}
    lines = []
    for o in orders:
        st = status_map.get(o["status"], o["status"])
        extra = f" · {o['city']}" if o.get("city") else ""
        lines.append(f"#{o['id']} · {o['product']}{extra} · {st}")
    await message.answer("Твои заказы:\n\n" + "\n".join(lines))


@router.message(F.text == "Профиль")
async def profile(message: Message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user or not user.get("registered"):
        await message.answer("Не зарегистрирован. /reg")
        return
    text = (
        f"<b>Профиль</b>\n\n"
        f"Имя: {user.get('name', '—')}\n"
        f"Telegram: {user.get('telegram', '—')}\n"
        f"ID: <code>{uid}</code>"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "Помощь")
@router.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "Спектр — документы.\n\n"
        "/start — начало\n"
        "/reg — регистрация\n"
        "Каталог — список и заказ\n"
        "Мои заказы — история\n"
        "Профиль — данные"
    )


@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()
