FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY lstm_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy necessary files
COPY tech_prototype/web/lstm_predictor.py /app/tech_prototype/web/
COPY tech_prototype/__init__.py /app/tech_prototype/
COPY tech_prototype/web/__init__.py /app/tech_prototype/web/
COPY data/ /app/data/
COPY lstm_service/app.py .

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
