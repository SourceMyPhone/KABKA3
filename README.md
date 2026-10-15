# Spektr Bot

Telegram-бот: каталог, регистрация, заказы с анкетой, админ-панель.

## Быстрый старт

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# отредактируй .env — впиши BOT_TOKEN и ADMIN_ID

python bot.py
```

## Переменные окружения

| Переменная   | Описание                          |
|--------------|-----------------------------------|
| `BOT_TOKEN`  | токен от @BotFather               |
| `ADMIN_ID`   | твой Telegram user id             |
| `DB_PATH`    | путь к SQLite (по умолчанию spektr.db) |

Секреты **не** хранятся в коде. Файл `.env` в `.gitignore`.

## Клиент

- `/start` — приветствие
- `/reg` — регистрация (имя + @telegram)
- **Каталог** → товар → **Оформить заказ**
- Анкета заказа:
  1. Город
  2. Способ (курьер / закладка / почта)
  3. Время
  4. Комментарий
- Подтверждение → заказ уходит админу
- Мои заказы / Профиль / Помощь

## Админ

- Уведомление о каждом заказе с кнопками **Принять** / **Отклонить**
- Клиент получает результат
- Панель (`Админ` или `/admin`): статистика, заказы, логи

## Структура

```
spektr-bot/
├── bot.py
├── config.py
├── db.py
├── keyboards.py
├── handlers/
│   ├── user.py
│   └── admin.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Безопасность при публикации на GitHub

1. В репозитории только `.env.example` (без реальных токенов).
2. `.env`, `*.db`, `venv/` — в `.gitignore`.
3. Если токен когда-либо светился — **отзови** его у @BotFather и создай новый.
4. `ADMIN_ID` только через env.

## Лицензия

MIT
