from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from datetime import datetime, timedelta
import random

app = Flask(__name__)

# === CONFIG ===
BOT_TOKEN = '7219594847:AAErvN0Ehhjxip_f4nztBtJ6z1gUkYPSYng'
CHAT_ID = 5596809359  # replace with your chat id
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Simulated OHLC candle store
ohlc_data = []

# Breakout/breakdown threshold
premium_ce = 80
premium_pe = 80

# --- Simulate 15-min OHLC Candle ---
def generate_ohlc():
    now = datetime.now()
    base_price = 25200
    last_close = ohlc_data[-1]['close'] if ohlc_data else base_price
    open_price = last_close
    high = open_price + random.randint(10, 50)
    low = open_price - random.randint(10, 50)
    close = random.randint(low, high)
    candle = {
        "time": now.strftime('%Y-%m-%d %H:%M'),
        "open": open_price,
        "high": high,
        "low": low,
        "close": close
    }
    ohlc_data.append(candle)
    if len(ohlc_data) > 96:  # 24 hours of 15min candles
        ohlc_data.pop(0)

# --- Calculate Levels from last N candles ---
def calculate_levels(n=6):
    recent = ohlc_data[-n:] if len(ohlc_data) >= n else ohlc_data
    highs = [c['high'] for c in recent]
    lows = [c['low'] for c in recent]
    return max(highs), min(lows)  # resistance, support

# --- Get current price (latest close) ---
def get_current_price():
    return ohlc_data[-1]['close'] if ohlc_data else 25200

# --- Trade Suggestion ---
def get_trade_suggestion():
    price = get_current_price()
    resistance, support = calculate_levels()

    if price > resistance:
        return {
            "type": "Breakout",
            "side": "CE",
            "strike": resistance,
            "entry_condition": f"Buy if premium < ₹{premium_ce}",
            "target": "₹130",
            "stoploss": "₹60",
            "price": price,
            "support": support,
            "resistance": resistance,
        }
    elif price < support:
        return {
            "type": "Breakdown",
            "side": "PE",
            "strike": support,
            "entry_condition": f"Buy if premium < ₹{premium_pe}",
            "target": "₹130",
            "stoploss": "₹60",
            "price": price,
            "support": support,
            "resistance": resistance,
        }
    else:
        return None

# --- Send Message to Telegram ---
def send_telegram(text, chat_id=CHAT_ID):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram Error:", e)

# --- Format Suggestion ---
def format_trade_message(data):
    return f"""
📈 NIFTY 50 {data['type']}!
Price: {data['price']}
Support: {data['support']}
Resistance: {data['resistance']}
✅ Suggested {data['side']}: {data['strike']} {data['side']} ({data['entry_condition']})
🎯 Target: {data['target']}
🛑 Stop-loss: {data['stoploss']}
🕒 Time: {datetime.now().strftime('%I:%M %p')}
"""

# --- Scheduled Check for Alert ---
def check_for_alert():
    generate_ohlc()
    suggestion = get_trade_suggestion()
    if suggestion:
        msg = format_trade_message(suggestion)
        send_telegram(msg)
        print("[SENT ALERT]", msg)
    else:
        print("[NO TRADE] Current price:", get_current_price())

# --- Flask Root Route ---
@app.route('/')
def home():
    return "✅ Bot is Running."

# --- Telegram Webhook Route ---
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    if "message" in data:
        message = data["message"]
        text = message.get("text", "")
        chat_id = message["chat"]["id"]

        if text == "/start":
            suggestion = get_trade_suggestion()
            if suggestion:
                msg = format_trade_message(suggestion)
            else:
                msg = f"📊 No breakout/breakdown. NIFTY is stable at {get_current_price()}.\nSupport/Resistance: {calculate_levels()}"
            send_telegram(msg, chat_id)

    return "OK", 200

# --- Scheduler Setup ---
scheduler = BackgroundScheduler()
scheduler.add_job(check_for_alert, 'interval', minutes=5)
scheduler.start()

# --- Start the App ---
if __name__ == "__main__":
    # Preload with 10 candles
    for _ in range(10):
        generate_ohlc()
    print("✅ Bot running on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000)
