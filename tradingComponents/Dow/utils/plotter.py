from datetime import datetime
import os
from io import BytesIO
from typing import Optional

import mplfinance as mpf
import pandas as pd

root_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')


def plot_candle_chart(df: pd.DataFrame, peaks: list[int] = [], valleys: list[int] = [], trend_info=None, sma: Optional[int] = None, symbol="NOT_PASSED",
                      return_img_buffer: bool = False, show_candles: Optional[int] = None):
    """Plot a candlestick chart with optional trend info, peaks, valleys."""
    # Create addplot objects for peaks and valleys
    if show_candles:
        # Adjust peaks and valleys indices for the sliced dataframe
        df_len = len(df)
        peaks = [p for p in peaks if p >= df_len - show_candles]
        valleys = [v for v in valleys if v >= df_len - show_candles]
        # Adjust indices to new positions
        peaks = [p - (df_len - show_candles) for p in peaks]
        valleys = [v - (df_len - show_candles) for v in valleys]
        df = df[-show_candles:]

    apds = []

    if len(peaks) > 0:
        peak_data = pd.Series(index=df.index, dtype=float)
        peak_data[df.index[peaks]] = df['Close'].iloc[peaks]
        apds.append(mpf.make_addplot(peak_data, type='scatter', markersize=100,
                                     marker='^', color='red', label='Peaks'))
    if len(valleys) > 0:
        valley_data = pd.Series(index=df.index, dtype=float)
        valley_data[df.index[valleys]] = df['Close'].iloc[valleys]
        apds.append(mpf.make_addplot(valley_data, type='scatter', markersize=100,
                                     marker='v', color='green', label='Valleys'))

    if sma:
        apds.append(
            mpf.make_addplot(df['Close'].rolling(window=sma).mean(), label=f'SMA ({sma})', color='orange')
        )

    # Create title
    if trend_info:
        trend_title = f"{trend_info['direction']} - {trend_info['phase']} | Power: {trend_info['strength']:.5f} | Price: {trend_info['price']:.5f}"
    else:
        trend_title = "No Clear Trend Detected"

    # Define the style
    style = mpf.make_mpf_style(base_mpf_style='yahoo', gridstyle=':', gridcolor='gray')

    # Plot
    if return_img_buffer:
        buf = BytesIO()
        mpf.plot(df, type='candle', addplot=apds, title=trend_title,
                 ylabel=f'Price ({symbol})', style=style, volume=True,
                 savefig=dict(fname=buf, dpi=150, format='png'))
        buf.seek(0)
        return buf
    else:
        mpf.plot(df, type='candle', addplot=apds, title=trend_title,
                 ylabel=f'Price ({symbol})', style=style, volume=True)
