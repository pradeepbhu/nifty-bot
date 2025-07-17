import requests
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request

app = Flask(__name__)

# --- Telegram Configuration ---
BOT_TOKEN = '7219594847:AAErvN0Ehhjxip_f4nztBtJ6z1gUkYPSYng'
CHAT_ID = 5596809359

# --- Levels ---
BREAKOUT_LEVEL = 25250
BREAKDOWN_LEVEL = 25100


# --- Get NIFTY Live Price ---
def get_nifty_price():
    try:
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/option-chain"
        }
        session = requests.Session()
        session.headers.update(headers)
        session.get("https://www.nseindia.com", timeout=5)  # Fetch cookies
        res = session.get(url, timeout=5)
        data = res.json()
        return float(data['records']['underlyingValue'])
    except Exception as e:
        print(f"[ERROR] Failed to fetch price: {e}")
        return None


# --- Send Telegram Message ---
def send_telegram(msg, chat_id=CHAT_ID):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": msg}
    try:
        res = requests.post(url, data=payload)
        print(f"[✔] Telegram Sent: {msg}")
    except Exception as e:
        print(f"[ERROR] Telegram failed: {e}")


# --- Log Alerts to File ---
def log_alert(message):
    with open("alerts.log", "a") as file:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        file.write(f"[{timestamp}] {message}\n")


# --- Check and Alert if Needed ---
def check_nifty():
    price = get_nifty_price()
    if not price:
        print("❌ Failed to fetch price")
        return

    message = ""
    if price > BREAKOUT_LEVEL:
        message = f"📈 Breakout! NIFTY at {price}. Suggest CE."
    elif price < BREAKDOWN_LEVEL:
        message = f"📉 Breakdown! NIFTY at {price}. Suggest PE."
    else:
        print(f"NIFTY Stable: {price}")
        return

    send_telegram(message)
    log_alert(message)


# --- Flask endpoint for manual trigger ---
@app.route('/')
def manual_check():
    check_nifty()
    return "✅ NIFTY checked"


# --- Flask endpoint to handle Telegram webhook ---
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json()

    if "message" in data:
        msg = data['message']
        text = msg.get("text", "")
        user_chat_id = msg['chat']['id']

        if text == "/start":
            send_telegram("👋 Welcome! Use /price to get NIFTY value.", chat_id=user_chat_id)

        elif text == "/price":
            price = get_nifty_price()
            if price:
                send_telegram(f"💹 NIFTY current price: {price}", chat_id=user_chat_id)
            else:
                send_telegram("❌ Could not fetch NIFTY price.", chat_id=user_chat_id)

    return "OK", 200


# --- Scheduler runs every 5 mins ---
scheduler = BackgroundScheduler()
scheduler.add_job(check_nifty, 'interval', minutes=5)
scheduler.start()


# --- Set Webhook when starting ---
def set_webhook():
    # Use your actual public HTTPS URL from ngrok or deployment
    public_url = "https://your-ngrok-or-server-url.com"
    webhook_url = f"{public_url}/{BOT_TOKEN}"
    res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}")
    print("Webhook set:", res.json())


# --- Main Entry ---
if __name__ == '__main__':
    print("✅ Bot running on http://localhost:10000 ...")
    # Uncomment this line if using ngrok or have a public URL
    # set_webhook()
    app.run(host='0.0.0.0', port=10000)
