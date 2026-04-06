from flask import Flask, request, render_template_string
import sqlite3
import requests
import re

app = Flask(__name__)

# ================= CONFIG ================= #
TELEGRAM_TOKEN = "8773521279:AAE4ogE89y7Tiq1JpSmbJEiXlmZwVjDgczI"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

ALLOWED_CHATS = [6929050061]   # make sure correct
DB_NAME = "stock.db"

# ================= DATABASE ================= #
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS hdpe_stock 
                 (item_code TEXT PRIMARY KEY, meters REAL)""")

    conn.commit()
    conn.close()

# ✅ IMPORTANT (RUN ALWAYS)
init_db()


# ================= TELEGRAM ================= #
def send_message(chat_id, text):
    try:
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text
        })
    except Exception as e:
        print("Send Error:", e)


# ================= SAFE WEBHOOK ================= #
@app.route("/telegram", methods=["POST"])
def telegram():
    try:
        data = request.get_json()
        print("Incoming:", data)

        if not data or "message" not in data:
            return "OK"

        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "").lower()

        # 🔥 ALWAYS REPLY (TEST)
        send_message(chat_id, f"Received: {text}")

        return "OK"

    except Exception as e:
        print("ERROR:", str(e))
        return "OK"


# ================= SIMPLE UI ================= #
@app.route("/")
def home():
    return "Bot is running ✅"


# ================= MAIN ================= #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
