from flask import Flask, request
import re
import sqlite3
import requests
import os

app = Flask(__name__)

# YOUR BOT CONFIG
TELEGRAM_TOKEN = "8773521279:AAG-vazTqy3Vd9wVvtCDSqvTs2TfVn1FU4w`"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
ALLOWED_CHATS = [6929050061, 8773521279]

def init_db():
    conn = sqlite3.connect('stock.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stock 
                 (item_name TEXT PRIMARY KEY, quantity REAL)''')
    conn.commit()
    conn.close()

INITIAL_STOCK = {
    "pn 100 8 kg": 1000.0,
    "pn 50 5 kg": 500.0,
}

def send_telegram_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    requests.post(url, data=payload)

def update_stock(item_name, quantity):
    conn = sqlite3.connect('stock.db')
    c = conn.cursor()
    c.execute("SELECT quantity FROM stock WHERE item_name=?", (item_name,))
    result = c.fetchone()
    if result:
        new_stock = max(0, result[0] - quantity)
        c.execute("UPDATE stock SET quantity=? WHERE item_name=?", (new_stock, item_name))
        conn.commit()
        conn.close()
        return new_stock
    conn.close()
    return None

@app.route("/telegram", methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    if not data or 'message' not in data: return "OK"
    
    message = data['message']
    chat_id = message['chat']['id']
    
    if chat_id not in ALLOWED_CHATS: return "OK"
    
    text = message.get('text', '').lower().strip()
    
    pattern = r'(\d+(?:\.\d+)?)\s*meter\s*(pn\s*\d+\s*\d+\s*kg)'
    match = re.search(pattern, text)
    
    if match:
        meters = float(match.group(1))
        item = match.group(2).strip()
        remaining = update_stock(item, meters) or INITIAL_STOCK.get(item, 0) - meters
        
        response = f"✅ <b>ORDER OK</b>\n📏 <b>{meters}m</b> <code>{item}</code>\n📦 <b>{remaining:.1f}m</b> LEFT"
        send_telegram_message(chat_id, response)
    elif text == "/stock":
        conn = sqlite3.connect('stock.db')
        c = conn.cursor()
        c.execute("SELECT item_name, quantity FROM stock")
        stocks = c.fetchall()
        conn.close()
        msg = "📊 <b>STOCK:</b>\n" + "\n".join([f"• <code>{i}</code> <b>{q:.1f}m</b>" for i,q in stocks])
        send_telegram_message(chat_id, msg or "📭 Empty")
    else:
        send_telegram_message(chat_id, "📋 Send: <code>93 meter pn 100 8 kg</code>")
    
    return "OK"

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
