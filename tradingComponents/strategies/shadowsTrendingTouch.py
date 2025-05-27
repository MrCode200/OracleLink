from typing import Optional
from pandas import DataFrame
from pandas_ta import sma as create_sma
import logging

logger = logging.getLogger("oracle.link")


### Return stop based on shadow size

class ShadowsTrendingTouch:
    def __init__(
            self,
            sma_period: int = 7,
            shadow_to_body_ratio: float = 1.25,
            shadow_multiplier: int = 1,
            opposite_shadow_to_body_ratio_limit: Optional[float] = 0.25,
            ignore_sma_touch: bool = False
    ):
        self.sma_period = sma_period
        self.shadow_to_body_ratio = shadow_to_body_ratio
        self.shadow_multiplier = shadow_multiplier
        self.opposite_shadow_to_body_ratio_limit = opposite_shadow_to_body_ratio_limit # shadow multiplier
        self.ignore_sma_touch: bool = ignore_sma_touch

    def evaluate(self, df: DataFrame) -> float:
        valid_df_range: int = self.sma_period + 1
        if len(df) < valid_df_range:
            return 0

        self_df = df.copy().iloc[-valid_df_range:]
        last_candle = self_df.iloc[-1]

        bullish_candle = last_candle.Open < last_candle.Close
        body_size = abs(last_candle.Open - last_candle.Close)

        # Candle Body doesn't touch SMA
        sma = create_sma(close=self_df.Close, length=self.sma_period)
        candle_above_sma = last_candle.Close > sma.iloc[-1]

        body_max: float = max(last_candle.Open, last_candle.Close)
        body_min: float = min(last_candle.Open, last_candle.Close)

        if body_min < sma.iloc[-1] < body_max:
            return 0

        # Bullish candle and above sma OR Bearish candle and below sma
        if bullish_candle != candle_above_sma:
            return 0

        # Find Shadow Touching Size
        if bullish_candle:
            shadows_touch_size = last_candle.Open - last_candle.Low
            opposite_shadow_size = last_candle.High - last_candle.Close
        else:
            shadows_touch_size = last_candle.High - last_candle.Open
            opposite_shadow_size = last_candle.Close - last_candle.Low

        # Shadow touching ratio
        if shadows_touch_size / body_size < self.shadow_to_body_ratio: # Green Close to High, Red Close to Low
            return 0

        # Opposite shadow small enough
        if (self.opposite_shadow_to_body_ratio_limit is not None and
                opposite_shadow_size / body_size > self.opposite_shadow_to_body_ratio_limit):
            return 0

        if self.ignore_sma_touch:
            return 1 if bullish_candle else -1

        # Check candles shadow is touching SMA
        padding: float = self.shadow_multiplier * shadows_touch_size
        if bullish_candle:
            if last_candle.Low - padding <= sma.iloc[-1]:
                return 1
        else:
            if last_candle.High + padding >= sma.iloc[-1]:
                return -1

        return 0
