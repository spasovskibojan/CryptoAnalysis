---
title: Crypto LSTM Predictor
emoji: 📈
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 7860
---

# LSTM Cryptocurrency Price Predictor

AI-powered cryptocurrency price prediction service using LSTM neural networks.

## Features
- Predicts future cryptocurrency prices
- Uses historical data and LSTM deep learning
- Provides price direction indicators
- Returns chart data for visualization

## API Endpoints

### `POST /predict`
Predict cryptocurrency price for a future date.

**Request:**
```json
{
  "symbol": "BTC-USD",
  "target_date": "2026-02-10"
}
```

**Response:**
```json
{
  "predicted_price": 45000.50,
  "target_date": "2026-02-10",
  "last_known_price": 44500.00,
  "direction": "UP",
  "days_ahead": 6,
  "labels": "[...dates...]",
  "values": "[...prices...]"
}
```

### `GET /health`
Health check endpoint.

## Tech Stack
- **FastAPI** - Modern web framework
- **TensorFlow** - Deep learning
- **LSTM** - Time series prediction
- **pandas/numpy** - Data processing
