# CryptoAnalysis - Deployment Guide

## Architecture

This application is deployed as a microservices architecture across two platforms:

- **Hugging Face Spaces**: LSTM Prediction Service (16GB RAM)
- **Render.com**: Django Web App + Technical Analysis + Fundamental Analysis

See [full deployment guide](./docs/DEPLOYMENT_DETAILED.md) for step-by-step instructions.

## Live URLs

**Main Application**: [Add your Render URL here]
**LSTM API**: [Add your Hugging Face Space URL here]

## Quick Deploy

1. Deploy LSTM to Hugging Face Spaces from `lstm_service/` directory
2. Deploy services to Render using Procfiles
3. Configure environment variables (see `.env.example`)

## Environment Variables

```bash
# Django Web App (Render)
SECRET_KEY=<random-secret-key>
DEBUG=False
ALLOWED_HOSTS=your-app.onrender.com
TA_SERVICE_URL=https://your-ta-service.onrender.com
FA_SERVICE_URL=https://your-fa-service.onrender.com
LSTM_SERVICE_URL=https://your-space.hf.space

# Services
No additional environment variables required for TA/FA services
```

## Local Development

See main README for local development with Docker Compose.
