from typing import Optional
from pandas import DataFrame
from pandas_ta import sma as create_sma
import logging

logger = logging.getLogger("oracle.link")


### Return stop based on shadow size

class ShadowsTrendingTouch:
    def __init__(self, sma_period: int = 7, shadow_to_body_ratio: float = 1.25,
                 shadow_padding_price: int = 2, opposite_shadow_to_body_ratio_limit: Optional[float] = 0.25):
        self.sma_period = sma_period
        self.shadow_to_body_ratio = shadow_to_body_ratio
        self.shadow_padding_price = shadow_padding_price
        self.opposite_shadow_to_body_ratio_limit = opposite_shadow_to_body_ratio_limit

    def evaluate(self, df: DataFrame) -> float:
        valid_df_range: int = self.sma_period + 1
        if len(df) < valid_df_range:
            return 0, {"Not Enough Data": True}

        self_df = df.copy().iloc[-valid_df_range:]
        last_candle = self_df.iloc[-1]
        sma = create_sma(close=self_df.Close, length=self.sma_period)

        candle_above_sma = last_candle.Close > sma.iloc[-1]
        bullish_candle = last_candle.Open < last_candle.Close
        body_size = abs(last_candle.Open - last_candle.Close)

        # Candle Body doesn't touch SMA
        body_max: float = max(last_candle.Open, last_candle.Close)
        body_min: float = min(last_candle.Open, last_candle.Close)
        if body_min < sma.iloc[-1] < body_max:
            return 0, {"Touch": True}

        # Bullish candle and above sma OR Bearish candle and below sma
        if bullish_candle != candle_above_sma:
            return 0, {"Correct Position": True}

        # Find Shadow Touching Size
        if bullish_candle:
            shadows_touch_size = last_candle.Open - last_candle.Low
            opposite_shadow_size = last_candle.High - last_candle.Close
        else:
            shadows_touch_size = last_candle.High - last_candle.Close
            opposite_shadow_size = last_candle.Open - last_candle.Low

        # ----------- DEBUG ------------
        data: dict[str, float] = {
            "body_size": body_size,
            "shadow_to_body_ratio": shadows_touch_size / body_size,
            "opposite_shadow_to_body_ratio": opposite_shadow_size / body_size
        }
        # ------------ DEBUG ------------

        # Shadow to Body Ratio is big enough
        if shadows_touch_size / body_size < self.shadow_to_body_ratio: # Green Close to High, Red Close to Low
            return 0, data # DEBUG: data

        # Opposite shadow small enough
        if (self.opposite_shadow_to_body_ratio_limit is not None and
                opposite_shadow_size / body_size > self.opposite_shadow_to_body_ratio_limit):
            return 0, data # DEBUG: data

        # Check candles touching
        if bullish_candle:
            if last_candle.Low - self.shadow_padding_price <= sma.iloc[-1]:
                return 1, data # DEBUG: data
        else:
            if last_candle.High + self.shadow_padding_price >= sma.iloc[-1]:
                return -1, data # DEBUG: data

        return 0, data # DEBUG: data
