from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from datetime import datetime
import os
import random

app = Flask(__name__)

# === CONFIGURATION ===
BOT_TOKEN = '7219594847:AAErvN0Ehhjxip_f4nztBtJ6z1gUkYPSYng'  # Replace with your bot token
CHAT_ID = 5596809359  # Replace with your chat ID
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

PREMIUM_CE = 80
PREMIUM_PE = 80

# === DATA STORES ===
market_data = {
    'NIFTY': {
        'ohlc': [],
        'last_fetch': None,
        'current_price': None,
        'support': None,
        'resistance': None
    },
    'BANKNIFTY': {
        'ohlc': [],
        'last_fetch': None,
        'current_price': None,
        'support': None,
        'resistance': None
    }
}

# === UTILITY FUNCTIONS ===
def fetch_nse_data(symbol):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    }
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers)
        if symbol == "NIFTY":
            url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
        elif symbol == "BANKNIFTY":
            url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20BANK"
        else:
            return None
        response = session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {symbol} data:", e)
        return None

def parse_nifty_data(data):
    if 'data' not in data:
        return None
    index_data = next((item for item in data['data'] if item['index'] in ['NIFTY 50', 'NIFTY BANK']), None)
    if not index_data:
        return None
    return {
        'open': index_data['open'],
        'high': index_data['dayHigh'],
        'low': index_data['dayLow'],
        'close': index_data['lastPrice'],
        'time': datetime.now().strftime('%Y-%m-%d %H:%M')
    }

def generate_simulated_candle(last_close, symbol):
    now = datetime.now()
    base_price = 25200 if symbol == 'NIFTY' else 52000
    open_price = last_close or base_price
    high = open_price + random.randint(10, 50)
    low = open_price - random.randint(10, 50)
    close = random.randint(int(low), int(high))
    return {
        "time": now.strftime('%Y-%m-%d %H:%M'),
        "open": open_price,
        "high": high,
        "low": low,
        "close": close
    }

def calculate_support_resistance(ohlc_data, n=6):
    if len(ohlc_data) < n:
        n = len(ohlc_data)
    recent = ohlc_data[-n:]
    highs = [c['high'] for c in recent]
    lows = [c['low'] for c in recent]
    return max(highs), min(lows)

# === TRADING LOGIC ===
def get_trade_suggestion(symbol):
    data = market_data[symbol]
    price = data['current_price']
    resistance = data['resistance']
    support = data['support']
    if not all([price, resistance, support]):
        return None
    if price > resistance:
        return {
            "symbol": symbol,
            "type": "Breakout",
            "side": "CE",
            "strike": round(resistance/100)*100,
            "entry_condition": f"Buy if premium < ₹{PREMIUM_CE}",
            "target": "₹130",
            "stoploss": "₹60",
            "price": price,
            "support": support,
            "resistance": resistance,
            "time": datetime.now().strftime('%I:%M %p')
        }
    elif price < support:
        return {
            "symbol": symbol,
            "type": "Breakdown",
            "side": "PE",
            "strike": round(support/100)*100,
            "entry_condition": f"Buy if premium < ₹{PREMIUM_PE}",
            "target": "₹130",
            "stoploss": "₹60",
            "price": price,
            "support": support,
            "resistance": resistance,
            "time": datetime.now().strftime('%I:%M %p')
        }
    return None

# === TELEGRAM FUNCTIONS ===
def send_telegram(text, chat_id=CHAT_ID):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram Error:", e)

def format_trade_message(data):
    return f"""
📈 <b>{data['symbol']} {data['type']} ALERT!</b>
──────────────────
💰 <b>Price</b>: {data['price']:.2f}
📉 <b>Support</b>: {data['support']:.2f}
📈 <b>Resistance</b>: {data['resistance']:.2f}
──────────────────
✅ <b>Suggested {data['side']}</b>: {data['strike']} {data['side']}
📌 <b>Condition</b>: {data['entry_condition']}
🎯 <b>Target</b>: {data['target']}
🛑 <b>Stop-loss</b>: {data['stoploss']}
──────────────────
🕒 <b>Time</b>: {data['time']}
"""

def format_status_message(symbol):
    data = market_data[symbol]
    return f"""
📊 <b>{symbol} Status</b>
──────────────────
💰 <b>Current Price</b>: {data['current_price']:.2f}
📉 <b>Support</b>: {data['support']:.2f}
📈 <b>Resistance</b>: {data['resistance']:.2f}
──────────────────
🕒 <b>Last Updated</b>: {datetime.now().strftime('%I:%M %p')}
"""

# === SCHEDULED TASKS ===
def update_market_data():
    for symbol in ['NIFTY', 'BANKNIFTY']:
        try:
            raw_data = fetch_nse_data(symbol)
            if raw_data:
                candle = parse_nifty_data(raw_data)
                if candle:
                    market_data[symbol]['ohlc'].append(candle)
                    market_data[symbol]['current_price'] = candle['close']
                    market_data[symbol]['last_fetch'] = datetime.now()
                    resistance, support = calculate_support_resistance(market_data[symbol]['ohlc'])
                    market_data[symbol]['resistance'] = resistance
                    market_data[symbol]['support'] = support
                    if len(market_data[symbol]['ohlc']) > 96:
                        market_data[symbol]['ohlc'] = market_data[symbol]['ohlc'][-96:]
                    continue
            last_close = market_data[symbol]['ohlc'][-1]['close'] if market_data[symbol]['ohlc'] else None
            candle = generate_simulated_candle(last_close, symbol)
            market_data[symbol]['ohlc'].append(candle)
            market_data[symbol]['current_price'] = candle['close']
            resistance, support = calculate_support_resistance(market_data[symbol]['ohlc'])
            market_data[symbol]['resistance'] = resistance
            market_data[symbol]['support'] = support
        except Exception as e:
            print(f"Error updating {symbol} data:", e)

def check_for_alerts():
    for symbol in ['NIFTY', 'BANKNIFTY']:
        suggestion = get_trade_suggestion(symbol)
        if suggestion:
            msg = format_trade_message(suggestion)
            send_telegram(msg)
            print(f"[ALERT SENT] {symbol}: {suggestion['type']} at {suggestion['price']:.2f}")
        else:
            print(f"[NO TRADE] {symbol} at {market_data[symbol]['current_price']}")

# === FLASK ROUTES ===
@app.route('/')
def home():
    return "🚀 NIFTY & BANKNIFTY Trading Bot is Running"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    if "message" in data:
        message = data["message"]
        text = message.get("text", "").strip().upper()
        chat_id = message["chat"]["id"]
        if text == "/START":
            responses = []
            for symbol in ['NIFTY', 'BANKNIFTY']:
                suggestion = get_trade_suggestion(symbol)
                if suggestion:
                    responses.append(format_trade_message(suggestion))
                else:
                    responses.append(format_status_message(symbol))
            send_telegram("\n\n".join(responses), chat_id)
        elif text == "/NIFTY":
            suggestion = get_trade_suggestion('NIFTY')
            msg = format_trade_message(suggestion) if suggestion else format_status_message('NIFTY')
            send_telegram(msg, chat_id)
        elif text == "/BANKNIFTY":
            suggestion = get_trade_suggestion('BANKNIFTY')
            msg = format_trade_message(suggestion) if suggestion else format_status_message('BANKNIFTY')
            send_telegram(msg, chat_id)
        elif text == "/PRICE":
            responses = [format_status_message(symbol) for symbol in ['NIFTY', 'BANKNIFTY']]
            send_telegram("\n\n".join(responses), chat_id)
        else:
            help_text = """
📊 <b>Available Commands</b>:
/start - Get market status
/nifty - NIFTY analysis
/banknifty - BANKNIFTY analysis
/price - Current prices
ℹ️ Bot checks breakout/breakdown every 5 minutes.
"""
            send_telegram(help_text, chat_id)
    return "OK", 200

# === INITIALIZATION ===
if __name__ == "__main__":
    update_market_data()
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_market_data, 'interval', minutes=5)
    scheduler.add_job(check_for_alerts, 'interval', minutes=5)
    scheduler.start()

    PORT = int(os.environ.get("PORT", 5000))  # Default to port 5000
    print(f"✅ Bot running on http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT)
