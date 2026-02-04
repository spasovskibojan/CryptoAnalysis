"""
LSTM Cryptocurrency Price Prediction Service
Standalone FastAPI service for Hugging Face Spaces
"""
import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import uvicorn

# Add parent directory to path to import lstm_predictor
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tech_prototype.web.lstm_predictor import predict_crypto_price

app = FastAPI(
    title="LSTM Crypto Price Predictor",
    description="AI-powered cryptocurrency price prediction using LSTM neural networks",
    version="1.0.0"
)

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Django domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PredictionRequest(BaseModel):
    symbol: str  # e.g., "BTC-USD", "ETH-USD"
    target_date: str  # Format: "YYYY-MM-DD"

class PredictionResponse(BaseModel):
    predicted_price: float
    target_date: str
    last_known_price: float
    direction: str  # "UP" or "DOWN"
    days_ahead: int
    labels: str  # JSON string for chart
    values: str  # JSON string for chart

@app.get("/")
def read_root():
    return {
        "service": "LSTM Cryptocurrency Price Predictor",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "/predict": "POST - Predict cryptocurrency price",
            "/health": "GET - Health check"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "lstm-predictor"}

@app.post("/predict", response_model=PredictionResponse)
async def predict_price(request: PredictionRequest):
    """
    Predict cryptocurrency price for a future date.
    
    - **symbol**: Cryptocurrency symbol (BTC-USD, ETH-USD, etc.)
    - **target_date**: Target date for prediction (YYYY-MM-DD)
    """
    try:
        # Get data directory path
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        
        # Call prediction function
        result = predict_crypto_price(
            symbol=request.symbol,
            target_date=request.target_date,
            data_dir=data_dir
        )
        
        return PredictionResponse(**result)
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Data not found for {request.symbol}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

if __name__ == "__main__":
    # For local testing
    uvicorn.run(app, host="0.0.0.0", port=7860)
