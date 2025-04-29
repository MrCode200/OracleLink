import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("oracle.link")


def fetch_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    """
    Fetches historical kline (candlestick) data from Yahoo Finance.
    Mimics the output structure of the original Binance function for core OHLCV columns.

    Parameters:
    - ticker (str): Ticker symbol compatible with Yahoo Finance
                    (e.g., 'AAPL', 'MSFT', 'BTC-USD', 'GC=F').
    - interval (str): Data interval. Common values:
                      Intraday: '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h'
                        (Note: Intraday data availability varies, often limited
                         to the last 60 days, '1h' up to 730 days).
                      Daily/Weekly/Monthly: '1d', '5d', '1wk', '1mo', '3mo'
                      Check yfinance documentation for full list and limitations.
    - limit (int): Number of *most recent* data points (candles) to retrieve.

    Returns:
    - pd.DataFrame: DataFrame containing Open, High, Low, Close, Volume,
                    with 'Open Time' (datetime) as the index.
                    Returns an empty DataFrame if data fetching fails or no data is found.
    """

    valid_intervals = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h',
                       '1d', '5d', '1wk', '1mo', '3mo']
    if interval not in valid_intervals:
        raise ValueError(f"Invalid interval: {interval}. Please use a valid yfinance interval.")

    period_to_fetch = None
    start_date = None
    end_date = datetime.now()

    intraday_short_limit = ['2m', '5m', '15m', '30m'] # Typically limited to 60 days
    intraday_medium_limit = ['60m', '90m', '1h'] # Typically limited to 730 days

    if interval == '1m':
         period_to_fetch = '7d'  # Yahoo Finance limits 1m data to 8 days, use 7 for safety
    elif interval in intraday_short_limit:
         period_to_fetch = '60d'
    elif interval in intraday_medium_limit:
         period_to_fetch = '730d'
    else:
        buffer_multiplier = 1.7 # ~7/4, covers weekends for daily/weekly etc.
        delta_unit = None
        if interval == '1d':
             delta_unit = timedelta(days=int(limit * buffer_multiplier))
        elif interval == '5d' or interval == '1wk':
             delta_unit = timedelta(weeks=int(limit * buffer_multiplier))
        elif interval == '1mo':
             delta_unit = timedelta(days=int(limit * buffer_multiplier * 30.5))
        elif interval == '3mo':
             delta_unit = timedelta(days=int(limit * buffer_multiplier * 91.5))

        if delta_unit:
            start_date = (end_date - delta_unit).strftime('%Y-%m-%d')
        else:
            period_to_fetch = 'max' # Fetch all available history
            logger.warning(f"Warning: Could not determine optimal fetch period for interval '{interval}'. Fetching 'max'.")


    # --- Fetch Data ---
    logger.debug(f"Fetching {symbol} data: Interval={interval}, Limit={limit} (Derived Period='{period_to_fetch}', Start='{start_date}')")
    try:
        if period_to_fetch:
            data = yf.download(
                tickers=symbol,
                period=period_to_fetch,
                interval=interval,
            )
        elif start_date:
            data = yf.download(
                tickers=symbol,
                start=start_date,
                end=end_date.strftime('%Y-%m-%d'),
                interval=interval,
            )
        else:
            logger.warning(f"Warning: Could not determine optimal fetch period for interval '{interval}'. Fetching 'max'")
            data = yf.download(symbol, interval=interval)

        # --- Process Data ---
        if data is None or data.empty:
            logger.error(f"Failed to fetch valid data for {symbol}. Got empty or insufficient data.")
            raise Exception(f"Failed to fetch {symbol} data: insufficient data points")

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]  # Flatten, due to multilevel return values
        
        data = data.tail(limit)
        return data

    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        raise


if __name__ == '__main__':
    # Test with BTC-USD to match Binance format
    print("--- Testing BTC-USD 1m data ---")
    df = fetch_klines(symbol='BTC-USD', interval='1m', limit=75)
    print("DataFrame type:", type(df))
    print("\nColumns:", df.columns)
    print("\nLast candle close price:")
    print(df.iloc[-1]['Close'])  # Using square brackets for more reliable access
    
    print("\nFull last row:")
    print(df.columns)  # For verification
    
    from pandas_ta import sma as create_sma
    print("\nSMA calculation:")
    sma = create_sma(close=df['Close'], length=7)
    print(sma.iloc[-1])  # Should also return just the float value
