import pandas as pd
import numpy as np
import time
from binance.client import Client
from scipy.signal import argrelextrema

# اتصال به Binance (نیازی به API Key نیست برای دیتا عمومی)
client = Client()
tickers = ["BTCUSDT", "DOGEUSDT"]


def get_klines(symbol='BTCUSDT', interval='1m', limit=100):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'Open', 'High', 'Low', 'Close',
        'Volume', 'Close time', 'Quote asset volume',
        'Number of trades', 'Taker buy base asset volume',
        'Taker buy quote asset volume', 'Ignore'
    ])
    df['Close'] = df['Close'].astype(float)
    df['timestamp'] = pd.to_datetime(df['Close time'], unit='ms')
    return df


def detect_support_resistance(price_data, order=15):
    local_max = argrelextrema(price_data['Close'].values, np.greater_equal, order=order)[0]
    local_min = argrelextrema(price_data['Close'].values, np.less_equal, order=order)[0]

    resistance = price_data.iloc[local_max]['Close'].values
    support = price_data.iloc[local_min]['Close'].values

    return support, resistance


def get_nearest_levels(close_price, support_levels, resistance_levels):
    nearest_support = max([level for level in support_levels if level < close_price], default=None)
    nearest_resistance = min([level for level in resistance_levels if level > close_price], default=None)
    return nearest_support, nearest_resistance


def check_breakout(last_close, nearest_support, nearest_resistance, timestamp):
    messages = []
    if nearest_support and last_close < nearest_support:
        messages.append(f"[{timestamp}] 🔻 Closed BELOW support {nearest_support:.2f} (Close: {last_close:.2f})")
    if nearest_resistance and last_close > nearest_resistance:
        messages.append(f"[{timestamp}] 🔺 Closed ABOVE resistance {nearest_resistance:.2f} (Close: {last_close:.2f})")
    return messages


# 🌀 اجرای مداوم هر 10 ثانیه
print("🔍 Running live breakout detector (press Ctrl+C to stop)...\n")
while True:
    try:
        for ticker in tickers:
            df = get_klines(symbol=ticker, interval='15m', limit=72)
            if len(df) < 10:
                continue

            support, resistance = detect_support_resistance(df.iloc[:-1], order=4)
            last_candle = df.iloc[-2]  # کندل بسته‌شده‌ی آخر
            last_close = last_candle['Close']
            timestamp = last_candle['timestamp']

            nearest_support, nearest_resistance = support[-1], resistance[-1]
            print(ticker, nearest_support, nearest_resistance)
            alerts = check_breakout(last_close, nearest_support, nearest_resistance, timestamp)

            for alert in alerts:
                print("🚨", alert)

    except Exception as e:
        print("❌ Error:", e)

    time.sleep(10)