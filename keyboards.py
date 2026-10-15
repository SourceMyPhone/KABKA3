# keyboards.py
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from config import CATALOG, DELIVERY


def main_kb(is_admin: bool = False):
    rows = [
        [KeyboardButton(text="Каталог"), KeyboardButton(text="Мои заказы")],
        [KeyboardButton(text="Профиль"), KeyboardButton(text="Помощь")],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="Админ")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def catalog_kb():
    buttons = []
    for item in CATALOG.values():
        buttons.append([
            InlineKeyboardButton(
                text=f"{item['title']} — {item['price_text']}",
                callback_data=f"cat:{item['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_kb(product_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оформить заказ", callback_data=f"order:{product_id}")],
        [InlineKeyboardButton(text="« К каталогу", callback_data="catalog")],
    ])


def delivery_kb():
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"deliv:{key}")]
        for key, label in DELIVERY.items()
    ]
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_order_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Подтвердить", callback_data="confirm_order"),
            InlineKeyboardButton(text="Отмена", callback_data="catalog"),
        ]
    ])


def admin_order_kb(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Принять", callback_data=f"adm_ok:{order_id}"),
            InlineKeyboardButton(text="Отклонить", callback_data=f"adm_no:{order_id}"),
        ]
    ])


def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Статистика", callback_data="adm_stats")],
        [InlineKeyboardButton(text="Заказы (все)", callback_data="adm_orders")],
        [InlineKeyboardButton(text="Заказы (ожидают)", callback_data="adm_orders_pending")],
        [InlineKeyboardButton(text="Логи", callback_data="adm_logs")],
        [InlineKeyboardButton(text="« Закрыть", callback_data="back_main")],
    ])


def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True
    )
