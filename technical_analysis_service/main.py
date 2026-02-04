from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import pandas as pd
# from strategies import (
#     RSIStrategy, MACDStrategy, StochasticStrategy, ADXStrategy,
#     CCIStrategy, MovingAverageStrategy, BollingerBandsStrategy, VolumeStrategy
# )
try:
    from strategies import (
        RSIStrategy, MACDStrategy, StochasticStrategy, ADXStrategy,
        CCIStrategy, #MovingAverageStrategy,
        BollingerBandsStrategy, VolumeStrategy,
        SMAStrategy, EMAStrategy, WMAStrategy
    )
except ImportError:
    from .strategies import (
        RSIStrategy, MACDStrategy, StochasticStrategy, ADXStrategy,
        CCIStrategy, MovingAverageStrategy, BollingerBandsStrategy, VolumeStrategy
    )
app = FastAPI()

class CandleData(BaseModel):
    Date: str
    Open: float
    High: float
    Low: float
    Close: float
    Volume: float

class AnalysisRequest(BaseModel):
    data: List[CandleData]

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

@app.post("/analyze")
async def analyze_data(request: AnalysisRequest):
    try:
        data_dicts = [item.dict() for item in request.data]
        df = pd.DataFrame(data_dicts)

        df["Date"] = pd.to_datetime(df["Date"])

        context = TechnicalAnalysisContext()
        df_indicators = context.compute_indicators(df).dropna()

        if df_indicators.empty:
            return {"overall_signal": "N/A", "overall_score": 0, "signals": []}

        last_row = df_indicators.iloc[-1]

        # per-indicator explanations
        detailed = []
        total_score = 0
        for strategy in context._strategies:
            info = strategy.explain(last_row)
            total_score += info["score"]
            detailed.append(info)

        overall_signal = context.generate_signal(last_row)

        return {
            "overall_signal": overall_signal,
            "overall_score": int(total_score),
            "signals": detailed
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def read_root():
    return {"status": "Technical Analysis Service is Running"}

@app.get("/health")
def health_check():
    """Lightweight health check endpoint for Render wake-up pings."""
    return {"status": "ok"}
