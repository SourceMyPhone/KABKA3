# Spektr Bot

Telegram-бот: каталог, регистрация, заказы с анкетой, админ-панель.

## Локальный запуск

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# заполни BOT_TOKEN и ADMIN_ID в .env
python bot.py
```

## Деплой на Railway (работает 24/7)

1. Залей репозиторий на GitHub (без `.env`, без `spektr.db`, без `__pycache__`).
2. Зайди на [railway.app](https://railway.app) → New Project → Deploy from GitHub repo.
3. Выбери репозиторий.
4. Variables → добавь:
   - `BOT_TOKEN` = токен бота
   - `ADMIN_ID` = твой Telegram ID
5. Deploy. В логах должно быть `Bot starting…`.

Railway сам подхватит `Procfile` / `railway.json`.

### Важно

- Не коммить `.env` и `spektr.db`.
- Удали из репо папку `__pycache__` если уже залита.
- SQLite на Railway живёт на эфемерном диске — при редеплое база может обнулиться. Для продакшена лучше Volume или внешняя БД.

## Анкета заказа

Одним сообщением, 4 строки:

```
Город
Способ (курьер / закладка / почта)
Время
Комментарий
```

Пример:

```
Москва
закладка
18:00–21:00
рядом с метро
```

## Переменные

| Переменная  | Описание        |
|-------------|-----------------|
| BOT_TOKEN   | токен @BotFather |
| ADMIN_ID    | твой Telegram ID |
| DB_PATH     | путь к SQLite    |

## Структура

```
bot.py  config.py  db.py  keyboards.py
handlers/user.py  handlers/admin.py
Procfile  railway.json  runtime.txt
.env.example  .gitignore  requirements.txt
```
