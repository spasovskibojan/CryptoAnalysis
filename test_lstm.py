#!/usr/bin/env python
"""
Тест скрипта за LSTM предвидување.
"""

import os
import sys

# Додавање на патека за импорт
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'tech_prototype', 'web'))

from lstm_predictor import predict_crypto_price
from datetime import datetime, timedelta

def test_lstm_prediction():
    """Тестирање на LSTM предвидување."""
    
    print("=" * 50)
    print("LSTM Предвидување - Тест")
    print("=" * 50)
    
    # Патека до податоци
    data_dir = os.path.join(BASE_DIR, 'data')
    
    # Тест параметри
    symbol = 'BTC-USD'
    target_date = (datetime.today() + timedelta(days=10)).strftime('%Y-%m-%d')
    
    print(f"\nКриптовалута: {symbol}")
    print(f"Целен датум: {target_date}")
    print("\nСе вчитуваат податоци...")
    
    try:
        # Предвидување
        result = predict_crypto_price(symbol, target_date, data_dir)
        
        print("\n" + "=" * 50)
        print("РЕЗУЛТАТИ")
        print("=" * 50)
        print(f"Предвидена цена: ${result['predicted_price']:.2f}")
        print(f"Тековна цена: ${result['last_known_price']:.2f}")
        print(f"Насока: {result['direction']}")
        print(f"Датум на предвидување: {result['target_date']}")
        print(f"Денови однапред: {result['days_ahead']}")
        
        # Промена во проценти
        change_pct = ((result['predicted_price'] - result['last_known_price']) / 
                      result['last_known_price']) * 100
        print(f"Очекувана промена: {change_pct:.2f}%")
        
        print("\n✅ Успешно предвидување!")
        
    except Exception as e:
        print(f"\n❌ Грешка: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_lstm_prediction()
