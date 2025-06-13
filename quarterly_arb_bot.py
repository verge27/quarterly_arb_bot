import os
import requests
import time
from datetime import datetime, timezone
import hmac
import hashlib
import logging

# --- Configuration ---
# Securely load API keys from environment variables
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# Trading Parameters
BASE_ASSET = "BTC"
QUOTE_ASSET = "USDT"
TRADE_QUANTITY = 0.001  # The amount of BTC to trade
BASIS_THRESHOLD = 25.0  # Trigger a trade if the basis (in USD) is wider than this

# Binance API Endpoints
BASE_FUTURES_URL = "https://fapi.binance.com"
EXCHANGE_INFO_URL = f"{BASE_FUTURES_URL}/fapi/v1/exchangeInfo"
SPOT_URL = f"https://api.binance.com/api/v3/ticker/price?symbol={BASE_ASSET}{QUOTE_ASSET}"
FUTURES_ORDER_URL = f"{BASE_FUTURES_URL}/fapi/v1/order"

# Configure logging
logging.basicConfig(filename="arb_trade_log.txt", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def log_message(level, message):
    """Logs a message to the console and the log file."""
    print(f"{datetime.now()}: {message}")
    if level == "info":
        logging.info(message)
    elif level == "error":
        logging.error(message)

def get_current_quarterly_symbol():
    """
    Fetches exchange info to dynamically find the current quarterly BTCUSDT symbol.
    """
    log_message("info", "Discovering current quarterly futures symbol...")
    try:
        response = requests.get(EXCHANGE_INFO_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Find all quarterly BTCUSDT contracts that are currently TRADING
        quarterly_contracts = [
            s for s in data['symbols']
            if s['baseAsset'] == BASE_ASSET 
            and s['quoteAsset'] == QUOTE_ASSET
            and s['contractType'] == 'QUARTERLY'
            and s['status'] == 'TRADING'
        ]

        if not quarterly_contracts:
            log_message("error", "No active quarterly contracts found.")
            return None

        # Find the one with the nearest delivery date in the future
        now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        future_contracts = [c for c in quarterly_contracts if c['deliveryDate'] > now_ts]
        
        if not future_contracts:
            log_message("error", "No quarterly contracts with a future delivery date found.")
            return None

        # Sort by delivery date and pick the earliest one
        current_contract = sorted(future_contracts, key=lambda x: x['deliveryDate'])[0]
        symbol = current_contract['symbol']
        log_message("info", f"Successfully identified current quarterly symbol: {symbol}")
        return symbol

    except requests.exceptions.RequestException as e:
        log_message("error", f"Could not fetch exchange info: {e}")
        return None

def get_signed_request_url(params):
    """Signs the request parameters and returns the full URL."""
    params['timestamp'] = int(time.time() * 1000)
    query_string = "&".join([f"{key}={params[key]}" for key in params])
    signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{FUTURES_ORDER_URL}?{query_string}&signature={signature}"

def get_price(url):
    """Fetches the price from a given Binance API URL."""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return float(response.json()["price"])
    except requests.exceptions.RequestException as e:
        log_message("error", f"Could not fetch price from {url}: {e}")
        return None

def execute_market_order(symbol, side, quantity):
    """Executes a simple market order."""
    log_message("info", f"Executing {side} order for {quantity} {symbol}...")
    params = { 'symbol': symbol, 'side': side, 'type': 'MARKET', 'quantity': quantity }
    headers = {"X-MBX-APIKEY": API_KEY}
    url = get_signed_request_url(params)
    try:
        response = requests.post(url, headers=headers, timeout=5)
        response.raise_for_status()
        log_message("info", f"SUCCESS: {response.json()}")
        return response.json()
    except requests.exceptions.RequestException as e:
        log_message("error", f"FAILED to execute order: {e.response.text if e.response else e}")
        return None

def check_trade_opportunity(futures_symbol):
    """Fetches prices, calculates basis, and executes trades if an opportunity exists."""
    spot_price = get_price(SPOT_URL)
    futures_price_url = f"{BASE_FUTURES_URL}/fapi/v1/ticker/price?symbol={futures_symbol}"
    futures_price = get_price(futures_price_url)

    if spot_price is None or futures_price is None:
        log_message("error", "Could not retrieve prices. Skipping check.")
        return

    basis = futures_price - spot_price
    log_message("info", f"Spot: ${spot_price:,.2f} | Futures ({futures_symbol}): ${futures_price:,.2f} | Basis: ${basis:,.2f}")

    if basis > BASIS_THRESHOLD:
        log_message("info", f"Basis ({basis:.2f}) > Threshold ({BASIS_THRESHOLD:.2f}). Executing SHORT arbitrage.")
        execute_market_order(symbol=futures_symbol, side="SELL", quantity=TRADE_QUANTITY)
    elif basis < -BASIS_THRESHOLD:
        log_message("info", f"Basis ({basis:.2f}) < Threshold (-{BASIS_THRESHOLD:.2f}). Executing LONG arbitrage.")
        execute_market_order(symbol=futures_symbol, side="BUY", quantity=TRADE_QUANTITY)

if __name__ == "__main__":
    if not API_KEY or not API_SECRET:
        print("ERROR: Please set BINANCE_API_KEY and BINANCE_API_SECRET environment variables.")
    else:
        # Discover the active quarterly contract at startup
        active_futures_symbol = get_current_quarterly_symbol()
        
        if active_futures_symbol:
            log_message("info", f"Arbitrage Bot Started. Monitoring {active_futures_symbol}. Press Ctrl+C to stop.")
            try:
                while True:
                    check_trade_opportunity(active_futures_symbol)
                    # Wait for 30 seconds before the next check
                    time.sleep(30)
            except KeyboardInterrupt:
                log_message("info", "Script stopped by user.")
        else:
            log_message("error", "Could not determine futures symbol. Exiting.")