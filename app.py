import requests
import time
from flask import Flask

app = Flask(__name__)

# Set your bot token and chat ID here
BOT_TOKEN = '7219594847:AAErvN0Ehhjxip_f4nztBtJ6z1gUkYPSYng'
CHAT_ID = 5596809359  # Must be an integer

# Your custom levels
BREAKOUT_LEVEL = 25250
BREAKDOWN_LEVEL = 25100

# NSE Headers (important to avoid blocking)
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "*/*",
    "Connection": "keep-alive",
    "Referer": "https://www.nseindia.com"
}

# Use session to store cookies
session = requests.Session()
session.headers.update(HEADERS)

def get_nifty_price():
    try:
        # Make initial call to nseindia.com to set cookies
        session.get("https://www.nseindia.com", timeout=5)

        url = "https://www.nseindia.com/api/quote-equity?symbol=NIFTY"
        response = session.get(url, timeout=10)
        data = response.json()

        price = float(data['priceInfo']['lastPrice'])
        return price

    except Exception as e:
        print("Error fetching NIFTY price:", e)
        return None

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        res = requests.post(url, data=payload, timeout=5)
        return res.status_code == 200
    except Exception as e:
        print("Failed to send Telegram message:", e)
        return False

@app.route('/')
def run_bot():
    nifty = get_nifty_price()
    if not nifty:
        return "❌ Failed to fetch price"

    message = f"NIFTY price: {nifty} → "

    if nifty > BREAKOUT_LEVEL:
        message += f"📈 Breakout! Suggest CE."
        send_telegram(f"📈 Breakout Alert!\nNIFTY is at {nifty}\nSuggest CE.")
    elif nifty < BREAKDOWN_LEVEL:
        message += f"📉 Breakdown! Suggest PE."
        send_telegram(f"📉 Breakdown Alert!\nNIFTY is at {nifty}\nSuggest PE.")
    else:
        message += f"Stable. No breakout."

    return message

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
