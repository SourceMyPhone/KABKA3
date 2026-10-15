# bot.py
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_ID
from db import init_db
from handlers import user, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("spektr")


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is empty. Copy .env.example to .env and fill BOT_TOKEN / ADMIN_ID.")
        sys.exit(1)
    if not ADMIN_ID:
        logger.warning("ADMIN_ID is 0 — admin features disabled until set.")

    init_db()
    logger.info("DB ready")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(user.router)
    dp.include_router(admin.router)

    logger.info("Bot starting…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
