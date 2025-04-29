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
    end_date = datetime.now() # Fetch up to today

    # Intraday data has limitations on historical reach
    intraday_short_limit = ['2m', '5m', '15m', '30m'] # Typically limited to 60 days
    intraday_medium_limit = ['60m', '90m', '1h']           # Typically limited to 730 days

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
                auto_adjust=False,  # Get raw OHLCV
                progress=False,     # Disable progress bar
                ignore_tz=False     # Keep timezone info if available
            )
        elif start_date:
            data = yf.download(
                tickers=symbol,
                start=start_date,
                end=end_date.strftime('%Y-%m-%d'),
                interval=interval,
                auto_adjust=False,
                progress=False,
                ignore_tz=False
            )
        else:
            logger.warning(f"Warning: Could not determine optimal fetch period for interval '{interval}'. Fetching 'max'")
            data = yf.download(symbol, interval=interval, auto_adjust=False, progress=False, ignore_tz=False)

        # --- Process Data ---
        if data is None or data.empty or len(data) < 2:  # Need at least 2 candles for SMA calculation
            logger.error(f"Failed to fetch valid data for {symbol}. Got empty or insufficient data.")
            raise Exception(f"Failed to fetch {symbol} data: insufficient data points")

        # Select the most recent 'limit' data points
        data = data.tail(limit)

        data.index.name = 'Open Time'

        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        output_columns = []

        for col in required_columns:
            if col in data.columns:
                output_columns.append(col)
                if col == 'Volume':
                    data[col] = data[col].astype(float)
            else:
                logger.warning(f"Column '{col}' not found in fetched data for {symbol}.")

        # Keep only the required columns in the standard order
        if not output_columns:
            raise Exception("Error: No standard OHLCV columns found in the fetched data.")

        data = data[output_columns]
        
        # Verify we have enough data for SMA calculation
        if len(data) < 8:  # Minimum required for 7-period SMA
            raise Exception(f"Insufficient data points for {symbol}: got {len(data)}, need at least 8")

        return data

    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        raise Exception(f"Failed to fetch {symbol} data: {str(e)}")


if __name__ == '__main__':
    # Example 1: Get latest 100 hours of Apple data
    print("--- Example 1: AAPL 1h ---")
    aapl_hourly = fetch_klines(symbol='AAPL', interval='1h', limit=100)
    if not aapl_hourly.empty:
        print(aapl_hourly.head())
        print(f"\nShape: {aapl_hourly.shape}")
        print(f"Index Type: {type(aapl_hourly.index)}")
        print(f"Data Types:\n{aapl_hourly.dtypes}")
    else:
        print("Failed to fetch AAPL hourly data.")

    print("\n" + "="*30 + "\n")

    # Example 2: Get latest 50 daily candles for Bitcoin
    print("--- Example 2: BTC-USD 1d ---")
    btc_daily = fetch_klines(symbol='BTC-USD', interval='1d', limit=50)
    if not btc_daily.empty:
        print(btc_daily.head())
        print(f"\nShape: {btc_daily.shape}")
        print(f"Index Type: {type(btc_daily.index)}")
        print(f"Data Types:\n{btc_daily.dtypes}")
    else:
        print("Failed to fetch BTC-USD daily data.")

    print("\n" + "="*30 + "\n")

    # Example 3: Get latest 60 5-minute candles for Gold Futures
    print("--- Example 3: GC=F 5m ---")
    # Note: Intraday data for futures might require specific ticker formats
    # and might have limited availability depending on your yfinance access/source.
    gold_5m = fetch_klines(symbol='GC=F', interval='5m', limit=60)
    if not gold_5m.empty:
        print(gold_5m.head())
        print(f"\nShape: {gold_5m.shape}")
        print(f"Index Type: {type(gold_5m.index)}")
        print(f"Data Types:\n{gold_5m.dtypes}")
    else:
        print("Failed to fetch GC=F 5m data (Intraday futures data can be sparse).")

    print("\n" + "="*30 + "\n")

    # Example 4: Invalid interval
    print("--- Example 4: Invalid Interval ---")
    try:
        fetch_klines(symbol='MSFT', interval='42m', limit=10)
    except ValueError as e:
        print(f"Caught expected error: {e}")