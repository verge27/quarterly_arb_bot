# BTC Quarterly Arbitrage Bot (Binance Testnet)

This repository contains a prototype framework for monitoring and executing trades based on the spread between BTC spot and quarterly futures prices on Binance. It is intended for **testnet use only**, with emphasis on connectivity, execution structure, and trading logic.

> ⚠️ **Important Note:** Quarterly futures contracts do **not carry a funding rate** like perpetual swaps. Therefore, funding rate arbitrage is not applicable. Instead, profitable strategies must focus on **basis trading**—exploiting the premium or discount between spot and futures prices.

---

## 🧠 Strategy Overview

This script was originally designed to capture arbitrage by comparing spot and quarterly BTC prices and executing trades when a threshold spread is observed.

While the funding arbitrage model was initially applied, quarterly contracts require a different approach—**basis trades**, which take advantage of the price differential as it converges toward spot over time.

---

## ⚙️ Features

- Connects to **Binance Testnet endpoints**
- Monitors BTC/USDT **spot price** and **quarterly futures price**
- Executes trades via:
  - Market orders (primary method)
  - Limit orders with adaptive price fallback if market order fails
- Supports **hedge mode** with manual `positionSide` configuration
- Logs trade events, failures, and API response details for debugging
- Includes structure to test and build on top of

---

## 📌 Potential Use Cases

- ✅ Prototype or test automation workflows for Binance Testnet
- ✅ Basis for developing a **BTC basis trade strategy**
- ✅ Sandbox for testing limit order logic, trailing executions, or hedge-mode support
- ❌ Not designed for live trading or funding-based arbitrage

---

## 📁 Files

- `quarterly_arb_bot.py` – Full strategy implementation and logic
- `README.md` – Project overview, limitations, and roadmap

---

## 🔧 Setup Requirements

- Python 3.8+
- Packages: `requests`, `hmac`, `hashlib`
- Binance Testnet API keys (https://testnet.binancefuture.com)

---

## ⚠️ Limitations & Key Learnings

- Binance **quarterly contracts have no funding rate**
- Market orders often fail on Testnet due to **lack of liquidity**
- Timestamp sync and HMAC authentication are essential for trade execution
- Proper **basis arbitrage** requires:
  - Calculating annualized basis (APR)
  - Monitoring expiry date
  - Managing delta risk

---

## 🚀 Next Steps

To evolve this bot into a production-ready basis strategy:
1. Add APR calculation logic
2. Integrate expiry detection via exchange info
3. Track historical basis premium for strategy backtesting
4. Expand error handling (e.g., websocket-based price feed)

---

## 📜 License

MIT License – Open source. Fork, contribute, or adapt freely.

---

## 🙌 Attribution

Originally developed as part of a trading strategy research and interview process. Published openly for learning and further development.
