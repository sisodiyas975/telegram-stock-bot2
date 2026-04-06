from flask import Flask, request, render_template_string
import sqlite3
import requests
import re

app = Flask(__name__)

# ================= CONFIG ================= #
TELEGRAM_TOKEN = "8773521279:AAE4ogE89y7Tiq1JpSmbJEiXlmZwVjDgczI"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

ALLOWED_CHATS = [6929050061]  # ⚠️ verify this
DB_NAME = "stock.db"
LOW_STOCK_LIMIT = 100

# ================= DEFAULT STOCK ================= #
DEFAULT_STOCK = {
    "1.0 inch 8 KG": 1285,
    "1.0 inch 10 KG": 666,
    "1.0 inch 12.5 KG": 863,
    "1.25 inch 8 KG": 274,
    "1.0 inch PE 100 8KG": 180,
}

# ================= DATABASE ================= #
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS hdpe_stock 
                 (item_code TEXT PRIMARY KEY, meters REAL)""")

    for item, qty in DEFAULT_STOCK.items():
        c.execute("INSERT OR IGNORE INTO hdpe_stock VALUES (?, ?)", (item, qty))

    conn.commit()
    conn.close()

# ✅ IMPORTANT FIX (runs on Render)
init_db()


def get_stock():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT item_code, meters FROM hdpe_stock")
    data = dict(c.fetchall())
    conn.close()
    return data


def update_stock(item, qty):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT meters FROM hdpe_stock WHERE item_code=?", (item,))
    row = c.fetchone()

    if row:
        new_qty = row[0] + qty
        c.execute("UPDATE hdpe_stock SET meters=? WHERE item_code=?", (new_qty, item))
    else:
        new_qty = qty
        c.execute("INSERT INTO hdpe_stock VALUES (?, ?)", (item, qty))

    conn.commit()
    conn.close()
    return new_qty


def deduct_stock(item, qty):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT meters FROM hdpe_stock WHERE item_code=?", (item,))
    row = c.fetchone()

    if not row:
        return None

    new_qty = max(0, row[0] - qty)
    c.execute("UPDATE hdpe_stock SET meters=? WHERE item_code=?", (new_qty, item))

    conn.commit()
    conn.close()
    return new_qty


# ================= TELEGRAM ================= #
def send_message(chat_id, text):
    res = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })
    print("Telegram response:", res.text)


# ================= FEATURES ================= #
def check_low_stock():
    stock = get_stock()
    low = [f"{k} - {v:.0f} MTR" for k, v in stock.items() if v <= LOW_STOCK_LIMIT]

    if low:
        msg = "⚠️ LOW STOCK ALERT:\n\n" + "\n".join(low)
        for chat in ALLOWED_CHATS:
            send_message(chat, msg)


def format_stock():
    s = get_stock()
    return f"""Sudhakar HDPE :

PE 100 :

1.0 inch 8 KG - {s.get('1.0 inch 8 KG', 0):.0f} MTR
1.0 inch 10 KG - {s.get('1.0 inch 10 KG', 0):.0f} MTR
1.0 inch 12.5 KG - {s.get('1.0 inch 12.5 KG', 0):.0f} MTR

PE 63 :

1.25 inch 8 KG - {s.get('1.25 inch 8 KG', 0):.0f} MTR

TUKDE :

1.0 inch PE 100 8 KG - {s.get('1.0 inch PE 100 8KG', 0):.0f} MTR"""


# ================= TELEGRAM WEBHOOK ================= #
@app.route("/telegram", methods=["POST"])
def telegram():
    data = request.get_json()
    print("Incoming:", data)

    if not data or "message" not in data:
        return "OK"

    chat_id = data["message"]["chat"]["id"]

    if chat_id not in ALLOWED_CHATS:
        print("Unauthorized:", chat_id)
        return "OK"

    text = data["message"].get("text", "").lower()

    if text == "hi":
        send_message(chat_id, "Bot working ✅")
        return "OK"

    if "/stock" in text:
        send_message(chat_id, format_stock())
        return "OK"

    add = re.search(r'add\s+(.+?)\s+(\d+)', text)
    if add:
        item = add.group(1).title()
        qty = float(add.group(2))

        new_qty = update_stock(item, qty)
        check_low_stock()

        send_message(chat_id, f"✅ Added {qty} MTR\n{item}\nNew: {new_qty:.0f}")
        return "OK"

    match = re.search(r'(\d+)\s*(?:m|meter).*?(\d+(?:\.\d+)?)\s*kg', text)
    if match:
        meters = float(match.group(1))
        kg = match.group(2)

        item_map = {
            "8": "1.0 inch 8 KG",
            "10": "1.0 inch 10 KG",
            "12.5": "1.0 inch 12.5 KG"
        }

        item = item_map.get(kg, "1.0 inch 8 KG")
        deduct_stock(item, meters)
        check_low_stock()

        send_message(chat_id, format_stock())
        return "OK"

    return "OK"


# ================= MOBILE UI ================= #
@app.route("/")
def panel():
    if request.args.get("pass") != "1234":
        return "❌ Unauthorized"

    stock = get_stock()

    return render_template_string("""
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <h2>📦 Stock Dashboard</h2>
    {% for k,v in stock.items() %}
        <div style="background:white;margin:10px;padding:10px;border-radius:10px;">
            <b>{{k}}</b><br>{{v}} MTR
        </div>
    {% endfor %}
    """, stock=stock)
