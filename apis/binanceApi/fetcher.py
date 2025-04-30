from binance.client import Client
import pandas as pd

def fetch_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    """
    Fetches historical kline (candlestick) data from Binance.

    Parameters:
    - symbol (str): Trading pair symbol (e.g., 'BTCUSDT').
    - interval (str): Kline interval (e.g., '1m', '15m', '1h', '1d').
    - limit (int): Number of data points to retrieve (max 1000).

    Returns:
    - pd.DataFrame: DataFrame containing open time, open, high, low, close, volume, etc.
    """
    # Initialize Binance client (no API key required for public data)
    client = Client()

    # Fetch klines
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)

    # Define column names as per Binance API documentation
    columns = [
        'Open Time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close Time', 'Quote Asset Volume', 'Number of Trades',
        'Taker Buy Base Asset Volume', 'Taker Buy Quote Asset Volume', 'Ignore'
    ]

    # Create DataFrame
    df = pd.DataFrame(klines, columns=columns)
    
    # Convert timestamp columns to datetime
    df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
    
    # Convert price and volume columns to float
    numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    df[numeric_columns] = df[numeric_columns].astype(float)
    
    # Set datetime index for mplfinance compatibility
    df.set_index('Open Time', inplace=True)
    
    return df

if __name__ == '__main__':
    df = fetch_klines(symbol='BTCUSDT', interval='1m', limit=100)
    print(df.iloc[-1]['Close Time'])