# db.py
import sqlite3
from datetime import datetime
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            name        TEXT,
            telegram    TEXT,
            registered  INTEGER DEFAULT 0,
            created_at  TEXT,
            updated_at  TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            username    TEXT,
            name        TEXT,
            telegram    TEXT,
            product_id  TEXT,
            product     TEXT,
            price       INTEGER,
            city        TEXT,
            delivery    TEXT,
            delivery_time TEXT,
            comment     TEXT,
            status      TEXT DEFAULT 'pending',
            created_at  TEXT,
            updated_at  TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            action      TEXT,
            details     TEXT,
            created_at  TEXT
        )
    """)

    cur.execute("PRAGMA table_info(orders)")
    cols = {row[1] for row in cur.fetchall()}
    if "city" not in cols:
        cur.execute("ALTER TABLE orders ADD COLUMN city TEXT")
    if "delivery" not in cols:
        cur.execute("ALTER TABLE orders ADD COLUMN delivery TEXT")
    if "delivery_time" not in cols:
        cur.execute("ALTER TABLE orders ADD COLUMN delivery_time TEXT")

    conn.commit()
    conn.close()


def log_action(user_id: int, action: str, details: str = ""):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (user_id, action, details, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_user(user_id: int, username: str = None, name: str = None, telegram: str = None, registered: int = None):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    existing = get_user(user_id)

    if existing:
        fields = []
        values = []
        if username is not None:
            fields.append("username = ?")
            values.append(username)
        if name is not None:
            fields.append("name = ?")
            values.append(name)
        if telegram is not None:
            fields.append("telegram = ?")
            values.append(telegram)
        if registered is not None:
            fields.append("registered = ?")
            values.append(registered)
        fields.append("updated_at = ?")
        values.append(now)
        values.append(user_id)
        cur.execute(f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?", values)
    else:
        cur.execute(
            "INSERT INTO users (user_id, username, name, telegram, registered, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, username or "", name or "", telegram or "", registered or 0, now, now)
        )
    conn.commit()
    conn.close()


def create_order(
    user_id: int,
    username: str,
    name: str,
    telegram: str,
    product_id: str,
    product: str,
    price: int,
    city: str = "",
    delivery: str = "",
    delivery_time: str = "",
    comment: str = "",
):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        """INSERT INTO orders
           (user_id, username, name, telegram, product_id, product, price,
            city, delivery, delivery_time, comment, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
        (user_id, username, name, telegram, product_id, product, price,
         city, delivery, delivery_time, comment, now, now)
    )
    order_id = cur.lastrowid
    conn.commit()
    conn.close()
    return order_id


def get_order(order_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_order_status(order_id: int, status: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
        (status, datetime.utcnow().isoformat(), order_id)
    )
    conn.commit()
    conn.close()


def get_user_orders(user_id: int, limit: int = 20):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_orders(limit: int = 50, status: str = None):
    conn = get_conn()
    cur = conn.cursor()
    if status:
        cur.execute(
            "SELECT * FROM orders WHERE status = ? ORDER BY id DESC LIMIT ?",
            (status, limit)
        )
    else:
        cur.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    users_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE registered = 1")
    users_reg = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders")
    orders_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    orders_pending = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'accepted'")
    orders_accepted = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'rejected'")
    orders_rejected = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM logs")
    logs_total = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(price), 0) FROM orders WHERE status = 'accepted'")
    revenue = cur.fetchone()[0]
    conn.close()
    return {
        "users_total": users_total,
        "users_reg": users_reg,
        "orders_total": orders_total,
        "orders_pending": orders_pending,
        "orders_accepted": orders_accepted,
        "orders_rejected": orders_rejected,
        "logs_total": logs_total,
        "revenue": revenue,
    }


def get_recent_logs(limit: int = 30):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
