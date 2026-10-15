# config.py
import os
from pathlib import Path

# load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

# Telegram — set via environment / .env, never commit real values
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or "0")

# Database
DB_PATH = os.getenv("DB_PATH", "spektr.db")

# Catalog
CATALOG = {
    "passport": {
        "id": "passport",
        "title": "Паспорт РФ",
        "desc": "Полный комплект. Ламинат, голограммы, УФ-метки. Внесение в базу — отдельно.",
        "price": 45000,
        "price_text": "от 45 000 ₽",
    },
    "driver": {
        "id": "driver",
        "title": "Водительское удостоверение",
        "desc": "Пластик, все категории. С проводкой или без.",
        "price": 25000,
        "price_text": "от 25 000 ₽",
    },
    "diploma": {
        "id": "diploma",
        "title": "Диплом / аттестат",
        "desc": "Любой ВУЗ, специальность, год. Бланки Гознак, мокрые печати.",
        "price": 15000,
        "price_text": "от 15 000 ₽",
    },
    "med": {
        "id": "med",
        "title": "Медицинские справки",
        "desc": "083/у, 086/у, нарколог, психиатр, допуск к оружию.",
        "price": 3000,
        "price_text": "от 3 000 ₽",
    },
    "reg": {
        "id": "reg",
        "title": "Временная регистрация",
        "desc": "Свидетельство по месту пребывания. Подтверждение по телефону.",
        "price": 8000,
        "price_text": "от 8 000 ₽",
    },
    "pass": {
        "id": "pass",
        "title": "Пропуск / удостоверение",
        "desc": "Служебные, корпоративные, ведомственные. По образцу или с нуля.",
        "price": 20000,
        "price_text": "от 20 000 ₽",
    },
}

# Delivery methods
DELIVERY = {
    "courier": "Курьер",
    "drop": "Закладка",
    "post": "Почта",
}
