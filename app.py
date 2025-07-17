import requests
import time
from flask import Flask

app = Flask(__name__)

BOT_TOKEN = '7219594847:AAErvN0Ehhjxip_f4nztBtJ6z1gUkYPSYng'
CHAT_ID = 5596809359  # <-- you'll paste your chat_id here

BREAKOUT_LEVEL = 25250
BREAKDOWN_LEVEL = 25100

def get_nifty_price():
    try:
        url = "https://www.nseindia.com/api/quote-equity?symbol=NIFTY"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
        res = requests.get(url, headers=headers, timeout=5)
        data = res.json()
        return float(data['priceInfo']['lastPrice'])
    except:
        return None

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=payload)

@app.route('/')
def run_bot():
    nifty = get_nifty_price()
    if not nifty:
        return "Failed to fetch price"
    
    if nifty > BREAKOUT_LEVEL:
        send_telegram(f"📈 Breakout! NIFTY at {nifty}. Suggest CE.")
    elif nifty < BREAKDOWN_LEVEL:
        send_telegram(f"📉 Breakdown! NIFTY at {nifty}. Suggest PE.")
    else:
        return f"NIFTY is stable: {nifty}"

    return f"Checked at NIFTY: {nifty}"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
