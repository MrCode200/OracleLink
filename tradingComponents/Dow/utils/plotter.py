from datetime import datetime
import os
from io import BytesIO
from typing import Optional

import mplfinance as mpf
import pandas as pd

root_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')


def plot_candle_chart(df: pd.DataFrame, peaks, valleys, trend_info=None, sma: Optional[int] = None, symbol="NOT_PASSED",
                      return_img_buffer: bool = False):
    """Plot a candlestick chart with optional trend info, peaks, valleys."""
    # Create addplot objects for peaks and valleys
    apds = []

    if len(peaks) > 0:
        peak_data = pd.Series(index=df.index, dtype=float)
        peak_data[peaks] = df['Close'].iloc[peaks]
        apds.append(mpf.make_addplot(peak_data, type='scatter', markersize=100,
                                     marker='^', color='red', label='Peaks'))
    if len(valleys) > 0:
        valley_data = pd.Series(index=df.index, dtype=float)
        valley_data[valleys] = df['Close'].iloc[valleys]
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
