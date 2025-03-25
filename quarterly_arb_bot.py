import requests
import pandas as pd
import time
from datetime import datetime, timezone, timedelta
import hmac
import hashlib
import urllib.parse
import json
import logging

# Binance Testnet API endpoints
BINANCE_SPOT_URL = "https://testnet.binance.vision/api/v3/ticker/price?symbol=BTCUSDT"
BINANCE_EXCHANGE_INFO_URL = "https://testnet.binancefuture.com/fapi/v1/exchangeInfo"
BINANCE_ORDER_URL = "https://testnet.binancefuture.com/fapi/v1/order"
BINANCE_ACCOUNT_URL = "https://testnet.binancefuture.com/fapi/v2/account"
BINANCE_FUTURES_PRICE_URL = "https://testnet.binancefuture.com/fapi/v1/ticker/price?symbol=BTCUSDT_250627"
BINANCE_FUNDING_RATE_URL = "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT"

# Alternative Funding Rate APIs
COINGECKO_FUNDING_URL = "https://api.coingecko.com/api/v3/derivatives"
COINAPI_FUNDING_URL = "https://rest.coinapi.io/v1/exchangerate/BTC/USD"  # Placeholder, requires authentication
COINAPI_KEY = "your_coinapi_key_here"

# Binance API keys (Replace with secure vault handling)
API_KEY = "413e3fadb0fa757063fd078061f796d40fcdddae088c5d2feb4ce9ec44928c2d"
API_SECRET = "103d17b7683548760cdd511e6649e25fe2368c339cf68478b802beca4c29d529"

# Configure logging
logging.basicConfig(filename="trade_log.txt", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Manually set position side based on Binance Futures settings
# If using One-Way Mode, set to "BOTH"
# If using Hedge Mode, set to "LONG" or "SHORT"
POSITION_SIDE = "LONG"  # Change to "SHORT" or "BOTH" as needed


def log_trade(action, details):
    logging.info(f"{action}: {details}")
    print(f"{action}: {details}")


# Execute a manual trade
def manual_execute_trade(side, quantity, contract):
    log_trade("Manual Trade Execution", f"Manually executing trade: {side} {quantity} {contract}")
    execute_trade(side, quantity, contract)


# Execute trade order with iterative price adjustment
def execute_trade(side, quantity, contract):
    timestamp = int(time.time() * 1000)

    # Attempt Market Order first
    query_string = f"symbol={contract}&side={side}&type=MARKET&quantity={quantity}&positionSide={POSITION_SIDE}&recvWindow=5000&timestamp={timestamp}"
    signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    request_url = f"{BINANCE_ORDER_URL}?{query_string}&signature={signature}"
    headers = {"X-MBX-APIKEY": API_KEY, "Content-Type": "application/json"}

    try:
        response = requests.post(request_url, headers=headers, timeout=5)
        response.raise_for_status()
        log_trade("Trade Executed", response.json())
        return
    except requests.exceptions.HTTPError as e:
        log_trade("Market Order Failed", f"HTTP Error: {response.text}")
    except requests.exceptions.RequestException as e:
        log_trade("Market Order Failed", f"Error: {str(e)}")

    # If Market Order Fails, Iteratively Adjust Limit Order Price
    log_trade("Falling Back to Limit Order", "Market Order failed, attempting a limit order")
    limit_price = get_futures_price()
    if limit_price:
        max_allowed_price = limit_price * 1.005  # Initial max range for limit orders
        min_allowed_price = limit_price * 0.995  # Initial min range for limit orders

        adjusted_limit_price = max_allowed_price if side == "BUY" else min_allowed_price

        while adjusted_limit_price >= min_allowed_price if side == "BUY" else adjusted_limit_price <= max_allowed_price:
            query_string = f"symbol={contract}&side={side}&type=LIMIT&quantity={quantity}&price={adjusted_limit_price}&timeInForce=GTC&positionSide={POSITION_SIDE}&recvWindow=5000&timestamp={timestamp}"
            signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            request_url = f"{BINANCE_ORDER_URL}?{query_string}&signature={signature}"

            try:
                response = requests.post(request_url, headers=headers, timeout=5)
                response.raise_for_status()
                log_trade("Trade Executed via Limit Order", response.json())
                return
            except requests.exceptions.HTTPError as e:
                log_trade("Limit Order Failed", f"HTTP Error: {response.text}")
                if "Limit price can't be higher" in response.text or "Limit price can't be lower" in response.text:
                    adjusted_limit_price *= 0.999 if side == "BUY" else 1.001  # Adjust step by step within allowed range
            except requests.exceptions.RequestException as e:
                log_trade("Limit Order Failed", f"Error: {str(e)}")
                break


# Get BTC Spot Price
def get_spot_price():
    try:
        response = requests.get(BINANCE_SPOT_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        return float(data["price"])
    except requests.exceptions.RequestException as e:
        log_trade("API Error (Spot Price)", str(e))
        return None


# Get BTC Quarterly Futures Price
def get_futures_price():
    try:
        response = requests.get(BINANCE_FUTURES_PRICE_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        return float(data["price"])
    except requests.exceptions.RequestException as e:
        log_trade("API Error (Futures Price)", str(e))
        return None


# Check trade opportunities
def check_trade_opportunity():
    spot_price = get_spot_price()
    futures_price = get_futures_price()

    if None in [spot_price, futures_price]:
        log_trade("Trade Check Skipped", "API Error Encountered - Retried 3 times")
        return

    log_trade("Trade Opportunity Checked", f"Spot Price: {spot_price}, Futures Price: {futures_price}")


if __name__ == "__main__":
    try:
        while True:
            check_trade_opportunity()
            time.sleep(60)
    except KeyboardInterrupt:
        log_trade("Script Stopped", "Manual Interrupt Detected. Exiting gracefully.")
        print("\nScript stopped by user. Exiting...")
