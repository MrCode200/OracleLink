from typing import Optional

from pandas import DataFrame

from tradingComponents.Dow import detect_dow_trend
from tradingComponents.Dow.utils.dowEnums import Trend


class KianStrat:
    def __init__(self, check_trend: bool = True):
        self.check_trend = check_trend

    def evaluate(
            self, df: DataFrame,
            trend_info: Optional[dict[str, any]] = None,
            peaks: Optional[list[int]] = None,
            valleys: Optional[list[int]] = None
    ) -> float:
        """
        ...

        :param df: DataFrame of klines
        :param trend_info: Dictionary of trend info
        :param peaks: Array of num of index candle for each peak
        :param valleys: Array of num of index candle for each valley
        :return: -1 (Sell), 0 (Hold), 1 (Buy) Or a float indicating the probability of a successful order(-1 - 1)
        """
        if trend_info is None or peaks is None or valleys is None:
            trend_info, peaks, valleys = detect_dow_trend(df)

        if peaks is None or valleys is None:
            return 0

        # Buy
        if (peaks[-1] < valleys[-1] and
            (not self.check_trend or trend_info['trend'] == Trend.UPTREND) and
            df.get('Close').iloc[-1] == ...): # <-- Under what price it should buy ###KIAN
            return 1

        # Sell
        elif (valleys[-1] < peaks[-1] and
              (not self.check_trend or trend_info['trend'] == Trend.DOWNTREND) and
              df.get('Close').iloc[-1] == ...): # <-- Under what price it should sell ###KIAN
            return -1

        else:
            return 0

