import pandas as pd
import ta
from abc import ABC, abstractmethod

class TechnicalIndicatorStrategy(ABC):
    name: str = "UNKNOWN"
    columns: list[str] = []

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        pass

    @abstractmethod
    def evaluate(self, row) -> int:
        pass

    def signal_from_score(self, score: int) -> str:
        if score > 0:
            return "BUY"
        if score < 0:
            return "SELL"
        return "HOLD"

    def explain(self, row) -> dict:
        score = int(self.evaluate(row))
        values = {}
        for c in self.columns:
            v = row.get(c, None)
            # Convert numpy types safely
            try:
                v = float(v) if v is not None else None
            except Exception:
                pass
            values[c] = v

        return {
            "name": self.name,
            "score": score,
            "signal": self.signal_from_score(score),
            "values": values
        }


class RSIStrategy(TechnicalIndicatorStrategy):
    name = "RSI"
    columns = ["RSI"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df["RSI"] = ta.momentum.RSIIndicator(df["Close"]).rsi()
        return df

    def evaluate(self, row) -> int:
        if row["RSI"] < 30:
            return 1
        elif row["RSI"] > 70:
            return -1
        return 0


class MACDStrategy(TechnicalIndicatorStrategy):
    name = "MACD"
    columns = ["MACD", "MACD_SIGNAL"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        macd = ta.trend.MACD(df["Close"])
        df["MACD"] = macd.macd()
        df["MACD_SIGNAL"] = macd.macd_signal()
        return df

    def evaluate(self, row) -> int:
        if row["MACD"] > row["MACD_SIGNAL"]:
            return 1
        return -1


class StochasticStrategy(TechnicalIndicatorStrategy):
    name = "Stochastic"
    columns = ["STOCH"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        stoch = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"])
        df["STOCH"] = stoch.stoch()
        return df

    def evaluate(self, row) -> int:
        if row["STOCH"] < 20:
            return 1
        elif row["STOCH"] > 80:
            return -1
        return 0


class ADXStrategy(TechnicalIndicatorStrategy):
    name = "ADX + EMA20 trend"
    columns = ["ADX", "EMA_20"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df["ADX"] = ta.trend.ADXIndicator(df["High"], df["Low"], df["Close"]).adx()
        df["EMA_20"] = ta.trend.EMAIndicator(df["Close"], window=20).ema_indicator()
        return df

    def evaluate(self, row) -> int:
        if row["ADX"] > 25:
            if row["Close"] > row["EMA_20"]:
                return 1
            else:
                return -1
        return 0


class CCIStrategy(TechnicalIndicatorStrategy):
    name = "CCI"
    columns = ["CCI"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"], df["Close"]).cci()
        return df

    def evaluate(self, row) -> int:
        if row["CCI"] < -100:
            return 1
        elif row["CCI"] > 100:
            return -1
        return 0




class SMAStrategy(TechnicalIndicatorStrategy):
    name = "SMA (20)"
    columns = ["SMA_20"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df["SMA_20"] = ta.trend.SMAIndicator(df["Close"], window=20).sma_indicator()
        return df

    def evaluate(self, row) -> int:
        return 1 if row["Close"] > row["SMA_20"] else -1


class EMAStrategy(TechnicalIndicatorStrategy):
    name = "EMA (20)"
    columns = ["EMA_20"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df["EMA_20"] = ta.trend.EMAIndicator(df["Close"], window=20).ema_indicator()
        return df

    def evaluate(self, row) -> int:
        return 1 if row["Close"] > row["EMA_20"] else -1


class WMAStrategy(TechnicalIndicatorStrategy):
    name = "WMA (20)"
    columns = ["WMA_20"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df["WMA_20"] = ta.trend.WMAIndicator(df["Close"], window=20).wma()
        return df

    def evaluate(self, row) -> int:
        return 1 if row["Close"] > row["WMA_20"] else -1



class BollingerBandsStrategy(TechnicalIndicatorStrategy):
    name = "Bollinger Bands"
    columns = ["BB_HIGH", "BB_LOW"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        bb = ta.volatility.BollingerBands(df["Close"])
        df["BB_HIGH"] = bb.bollinger_hband()
        df["BB_LOW"] = bb.bollinger_lband()
        return df

    def evaluate(self, row) -> int:
        if row["Close"] < row["BB_LOW"]:
            return 1
        elif row["Close"] > row["BB_HIGH"]:
            return -1
        return 0


class VolumeStrategy(TechnicalIndicatorStrategy):
    name = "Volume vs SMA20"
    columns = ["VOL_SMA_20"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df["VOL_SMA_20"] = ta.trend.SMAIndicator(df["Volume"], window=20).sma_indicator()
        return df

    def evaluate(self, row) -> int:
        if row["Volume"] > row["VOL_SMA_20"]:
            return 1
        return 0
