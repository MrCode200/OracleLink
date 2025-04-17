import ccxt
import pandas as pd

exchange = ccxt.binance()

def fetch_data(
        symbol: str,
        timeframe: str = '15m',
        lookback_minutes: int = 30
):
    """Fetch OHLCV data from Binance and prepare dataframe"""
    since = exchange.milliseconds() - lookback_minutes * 60 * 1000
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since)

    df = pd.DataFrame(ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')
    df.set_index('Date', inplace=True)

    return df.dropna()