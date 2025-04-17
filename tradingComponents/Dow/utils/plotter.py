import matplotlib.pyplot as plt


def plot_chart(df, peaks, valleys, trend_info=None, symbol="NOT_PASSED"):
    """Plot the price chart with trend analysis"""
    plt.figure(figsize=(14, 7))

    # Plot price data
    plt.plot(df['Close'], label='Close Price', color='royalblue', linewidth=1.5)

    # Plot peaks and valleys
    plt.scatter(df.index[peaks], df['Close'].iloc[peaks], color='red', label='Swing Highs', marker='^', s=80)
    plt.scatter(df.index[valleys], df['Close'].iloc[valleys], color='green', label='Swing Lows', marker='v', s=80)

    # Add connecting lines between successive peaks and valleys to visualize trend
    if len(peaks) >= 2:
        plt.plot(df.index[peaks[-2:]], df['Close'].iloc[peaks[-2:]], 'r--', alpha=0.7)
    if len(valleys) >= 2:
        plt.plot(df.index[valleys[-2:]], df['Close'].iloc[valleys[-2:]], 'g--', alpha=0.7)

    # Add title based on trend information
    if trend_info:
        title = f"{trend_info['direction']} - {trend_info['phase']} | Power: {trend_info['strength']:.5f} | Price: {trend_info['price']:.5f}"

        # Add color based on trend direction
        color = 'green' if trend_info['direction'] == 'Uptrend' else 'red' if trend_info[
                                                                                  'direction'] == 'Downtrend' else 'orange'
        plt.title(title, color=color, fontweight='bold')
    else:
        plt.title("No Clear Trend Detected", fontweight='bold')

    # Add labels and grid
    plt.xlabel('Date')
    plt.ylabel(f'Price ({symbol.split("/")[1]})')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # Show the chart
    plt.show()