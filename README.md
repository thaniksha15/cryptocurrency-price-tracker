# cryptocurrency-price-tracker
# 🚀 Crypto Pulse – Real-Time Cryptocurrency Market Intelligence

Crypto Pulse is a Python-based real-time cryptocurrency market tracking application. It uses Selenium to automatically collect cryptocurrency market data from CoinMarketCap and provides the information through a professional Tkinter desktop dashboard.

The application tracks the Top 10 cryptocurrencies, displays live market information, stores historical data in CSV format, and provides filtering, comparison, alerts, and price history visualization features.

---

## 📌 Project Description

Crypto Pulse is designed to automate cryptocurrency market data collection and monitoring.

The application uses Selenium WebDriver to open CoinMarketCap, load dynamically generated market data, extract the Top 10 cryptocurrency information, and display it in a desktop dashboard.

The collected information includes:

- Cryptocurrency Rank
- Cryptocurrency Name
- Current Price
- 1-Hour Change
- 24-Hour Change
- 7-Day Change
- Market Capitalization
- Trading Volume

The application automatically refreshes market data every 30 seconds and stores the collected information in a CSV file for historical tracking.

---

## 🎯 Objectives

- To automate cryptocurrency market data extraction.
- To monitor the Top 10 cryptocurrencies in real time.
- To provide a user-friendly desktop dashboard.
- To store historical cryptocurrency data.
- To visualize cryptocurrency price history.
- To provide custom filtering and comparison features.
- To create price alerts for selected cryptocurrencies.

---

## ✨ Features

### 📊 Real-Time Market Tracking
- Tracks the Top 10 cryptocurrencies.
- Automatically refreshes every 30 seconds.
- Displays current price and market statistics.

### 🔎 Custom Market Filter
Users can filter cryptocurrencies based on:

- Minimum Price
- Maximum Price
- Minimum 24-hour Change

### ⚖ Cryptocurrency Comparison
Users can select two cryptocurrencies and compare:

- Price
- 24-hour change
- 7-day change
- Market capitalization

### 🔔 Price Alerts
Users can create price alerts using:

- Above target price
- Below target price

The application displays an alert when the selected cryptocurrency reaches the target price.

### 📈 Price History Graph
The application provides a price history graph using Matplotlib.

Features include:

- Cryptocurrency search
- Individual coin selection
- Historical price visualization
- Timestamp-based graph
- Latest price indicator

### 📁 CSV Historical Storage
Market data is stored in:

```text
reports/crypto_history.csv
