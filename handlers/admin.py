# handlers/admin.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from config import ADMIN_ID
from db import (
    get_stats, get_all_orders, get_order,
    update_order_status, get_recent_logs, log_action
)
from keyboards import admin_kb

router = Router()


@router.message(F.text == "Админ")
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    log_action(message.from_user.id, "admin_panel")
    await message.answer("Админ-панель:", reply_markup=admin_kb())


@router.callback_query(F.data == "adm_stats")
async def adm_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    s = get_stats()
    text = (
        f"<b>Статистика</b>\n\n"
        f"Пользователи: {s['users_total']} (рег. {s['users_reg']})\n"
        f"Заказы всего: {s['orders_total']}\n"
        f"  · ожидают: {s['orders_pending']}\n"
        f"  · приняты: {s['orders_accepted']}\n"
        f"  · отклонены: {s['orders_rejected']}\n"
        f"Выручка (принятые): {s['revenue']:,} ₽\n"
        f"Логов: {s['logs_total']}"
    )
    await callback.message.edit_text(text, reply_markup=admin_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "adm_orders")
async def adm_orders(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    orders = get_all_orders(limit=20)
    if not orders:
        await callback.message.edit_text("Заказов нет.", reply_markup=admin_kb())
        await callback.answer()
        return
    status_map = {"pending": "⏳", "accepted": "✓", "rejected": "✗"}
    lines = []
    for o in orders:
        mark = status_map.get(o["status"], "?")
        city = o.get("city") or "—"
        lines.append(
            f"{mark} #{o['id']} {o['product']}\n"
            f"   {o['name']} | {o['telegram']} | {city}\n"
            f"   {o.get('delivery') or '—'} · {o.get('delivery_time') or '—'} | {o['price']:,} ₽"
        )
    text = "<b>Последние заказы</b>\n\n" + "\n\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n…"
    await callback.message.edit_text(text, reply_markup=admin_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "adm_orders_pending")
async def adm_orders_pending(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    orders = get_all_orders(limit=20, status="pending")
    if not orders:
        await callback.message.edit_text("Ожидающих нет.", reply_markup=admin_kb())
        await callback.answer()
        return
    lines = []
    for o in orders:
        lines.append(
            f"#{o['id']} {o['product']}\n"
            f"   {o['name']} | {o['telegram']}\n"
            f"   {o.get('city') or '—'} · {o.get('delivery') or '—'} · {o.get('delivery_time') or '—'}\n"
            f"   {o.get('comment') or '—'} | {o['price']:,} ₽"
        )
    text = "<b>Ожидают решения</b>\n\n" + "\n\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n…"
    await callback.message.edit_text(text, reply_markup=admin_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "adm_logs")
async def adm_logs(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    logs = get_recent_logs(limit=25)
    if not logs:
        await callback.message.edit_text("Логов нет.", reply_markup=admin_kb())
        await callback.answer()
        return
    lines = []
    for l in logs:
        ts = (l["created_at"] or "")[:19].replace("T", " ")
        lines.append(f"<code>{ts}</code> [{l['user_id']}] {l['action']} {l['details'] or ''}")
    text = "<b>Логи</b>\n\n" + "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n…"
    await callback.message.edit_text(text, reply_markup=admin_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_ok:"))
async def order_accept(callback: CallbackQuery, bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    order_id = int(callback.data.split(":")[1])
    order = get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    if order["status"] != "pending":
        await callback.answer(f"Уже: {order['status']}", show_alert=True)
        return
    update_order_status(order_id, "accepted")
    log_action(callback.from_user.id, "order_accept", f"#{order_id}")
    await callback.message.edit_text(
        (callback.message.text or "") + "\n\n<b>✓ ПРИНЯТ</b>",
        parse_mode="HTML"
    )
    await callback.answer("Принят")
    try:
        await bot.send_message(
            order["user_id"],
            f"Заказ #{order_id} принят.\n{order['product']}\n"
            f"{order.get('city') or ''} · {order.get('delivery') or ''}\n\n"
            "Ожидай дальнейших инструкций."
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_no:"))
async def order_reject(callback: CallbackQuery, bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    order_id = int(callback.data.split(":")[1])
    order = get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    if order["status"] != "pending":
        await callback.answer(f"Уже: {order['status']}", show_alert=True)
        return
    update_order_status(order_id, "rejected")
    log_action(callback.from_user.id, "order_reject", f"#{order_id}")
    await callback.message.edit_text(
        (callback.message.text or "") + "\n\n<b>✗ ОТКЛОНЁН</b>",
        parse_mode="HTML"
    )
    await callback.answer("Отклонён")
    try:
        await bot.send_message(
            order["user_id"],
            f"Заказ #{order_id} отклонён.\n{order['product']}"
        )
    except Exception:
        pass
