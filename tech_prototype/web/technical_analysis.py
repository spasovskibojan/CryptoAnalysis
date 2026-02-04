import pandas as pd
from .strategies import (
    RSIStrategy, MACDStrategy, StochasticStrategy, ADXStrategy,
    CCIStrategy, MovingAverageStrategy, BollingerBandsStrategy, VolumeStrategy
)

class TechnicalAnalysisContext:
    def __init__(self):
        self._strategies = [
            RSIStrategy(),
            MACDStrategy(),
            StochasticStrategy(),
            ADXStrategy(),
            CCIStrategy(),
            BollingerBandsStrategy(),
            VolumeStrategy(),
            SMAStrategy(),
            EMAStrategy(),
            WMAStrategy(),
        ]

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for strategy in self._strategies:
            df = strategy.compute(df)
        return df

    def generate_signal(self, row) -> str:
        score = 0
        for strategy in self._strategies:
            score += strategy.evaluate(row)

        if score >= 3:
            return "BUY"
        elif score <= -3:
            return "SELL"
        return "HOLD"

def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    context = TechnicalAnalysisContext()
    return context.compute_indicators(df)

def generate_signal(row) -> str:
    context = TechnicalAnalysisContext()
    return context.generate_signal(row)
