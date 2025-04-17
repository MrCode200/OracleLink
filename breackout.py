import numpy as np
from scipy.signal import argrelextrema


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

def breackout(df):
    support, resistance = detect_support_resistance(df.iloc[:-1], order=4)
    last_candle = df.iloc[-2]  # کندل بسته‌شده‌ی آخر
    last_close = last_candle['Close']
    timestamp = last_candle['timestamp']

    nearest_support, nearest_resistance = support[-1], resistance[-1]
    alerts = check_breakout(last_close, nearest_support, nearest_resistance, timestamp)
    if alerts :
        return alerts
    return None