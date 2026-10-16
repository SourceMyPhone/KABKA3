# api.py — HTTP endpoint for website orders
import json
import logging
from aiohttp import web

from config import ADMIN_ID, ORDER_SECRET
from db import create_order, log_action, upsert_user
from keyboards import admin_order_kb

logger = logging.getLogger("spektr.api")


def _fmt_order(data: dict) -> str:
    user = data.get("user") or {}
    items = data.get("items") or []
    payment = data.get("payment") or {}
    lines = []
    for it in items:
        fields = it.get("fields") or {}
        field_txt = ", ".join(f"{k}: {v}" for k, v in fields.items() if v)
        lines.append(f"• {it.get('title', '?')}" + (f"\n  {field_txt}" if field_txt else ""))
    items_block = "\n".join(lines) if lines else "—"

    if payment.get("method") == "crypto":
        pay = "Monero"
    else:
        t = "СБП" if payment.get("type") == "sbp" else "Карта"
        pay = f"{t} · {payment.get('bank', '—')} · {payment.get('fio', '—')}"

    return (
        f"<b>Заказ с сайта #{data.get('id', '—')}</b>\n\n"
        f"Клиент: {user.get('name', '—')}\n"
        f"Telegram: {user.get('tg', '—')}\n\n"
        f"<b>Позиции</b>\n{items_block}\n\n"
        f"Сумма: <b>{data.get('total', 0):,} ₽</b>\n"
        f"Город: {data.get('city', '—')}\n"
        f"Получение: {data.get('delivery', '—')}\n"
        f"Время: {data.get('time', '—')}\n"
        f"Комментарий: {data.get('comment') or '—'}\n"
        f"Оплата: {pay}"
    ).replace(",", " ")


async def handle_order(request: web.Request):
    bot = request.app["bot"]
    secret = request.headers.get("X-Order-Secret") or request.query.get("secret")
    if secret != ORDER_SECRET:
        return web.json_response({"ok": False, "error": "forbidden"}, status=403)

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)

    user = data.get("user") or {}
    tg = (user.get("tg") or "").strip()
    name = (user.get("name") or "").strip()
    items = data.get("items") or []
    if not items:
        return web.json_response({"ok": False, "error": "empty"}, status=400)

    # store first item as primary in DB (compat with bot orders table)
    first = items[0]
    product = first.get("title") or "Заказ с сайта"
    if len(items) > 1:
        product = product + f" +{len(items)-1}"

    # synthetic user_id from hash of tg if no numeric id
    uid = abs(hash(tg)) % (10**9) if tg else 0
    try:
        upsert_user(uid, username=tg.lstrip("@"), name=name, telegram=tg, registered=1)
    except Exception:
        pass

    order_id = create_order(
        user_id=uid,
        username=tg.lstrip("@"),
        name=name,
        telegram=tg,
        product_id=first.get("id") or "site",
        product=product,
        price=int(data.get("total") or 0),
        city=data.get("city") or "",
        delivery=data.get("delivery") or "",
        delivery_time=data.get("time") or "",
        comment=data.get("comment") or json.dumps(data.get("items"), ensure_ascii=False)[:500],
    )
    log_action(uid, "site_order", f"#{order_id} {product}")

    text = _fmt_order({**data, "id": order_id})
    try:
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                text,
                reply_markup=admin_order_kb(order_id),
                parse_mode="HTML",
            )
    except Exception as e:
        logger.exception("notify admin failed: %s", e)
        return web.json_response({"ok": False, "error": "notify failed"}, status=500)

    return web.json_response({"ok": True, "order_id": order_id})


async def handle_health(request: web.Request):
    return web.json_response({"ok": True})


def create_app(bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/health", handle_health)
    app.router.add_post("/api/order", handle_order)
    # CORS preflight
    async def options(request):
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-Order-Secret",
        })
    app.router.add_route("OPTIONS", "/api/order", options)

    @web.middleware
    async def cors_middleware(request, handler):
        if request.method == "OPTIONS":
            return await handler(request)
        resp = await handler(request)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Order-Secret"
        return resp

    app.middlewares.append(cors_middleware)
    return app
