"""
LSTM модул за предвидување на цени на криптовалути.
Базиран на PredictingDataFixed.ipynb
Со додадено кеширање на модели за побрзи предвидувања.
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout

# Suppress TensorFlow warnings for cleaner output
tf.get_logger().setLevel('ERROR')


class LSTMPredictor:
    """
    Класа за предвидување на цени користејќи LSTM невронска мрежа.
    Вклучува кеширање на модели за побрзо извршување.
    """
    
    # Cache validity period (in hours) - models older than this will be retrained
    CACHE_VALIDITY_HOURS = 24
    
    def __init__(self, data_dir, lookback=60, models_dir=None):
        """
        Иницијализација на предикторот.
        
        Args:
            data_dir: Патека до директориумот со податоци
            lookback: Број на минати денови за анализа (default: 60)
            models_dir: Патека до директориумот за кеширање на модели
        """
        self.data_dir = data_dir
        self.lookback = lookback
        self.model = None
        self.scaler = None
        self.close_scaler = None
        self.features = ['Open', 'High', 'Close', 'Volume']
        
        # Set up models directory for caching
        if models_dir is None:
            # Default: create 'models' folder next to 'data' folder
            self.models_dir = os.path.join(os.path.dirname(data_dir), 'models')
        else:
            self.models_dir = models_dir
            
        # Create models directory if it doesn't exist
        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir)
    
    def _get_model_path(self, symbol):
        """Get the path for cached model file."""
        return os.path.join(self.models_dir, f"{symbol}_lstm.keras")
    
    def _get_scaler_path(self, symbol):
        """Get the path for cached scaler file."""
        return os.path.join(self.models_dir, f"{symbol}_scaler.pkl")
    
    def _is_cache_valid(self, symbol):
        """
        Check if cached model exists and is still valid (not too old).
        
        Returns:
            bool: True if cache is valid and can be used
        """
        model_path = self._get_model_path(symbol)
        scaler_path = self._get_scaler_path(symbol)
        
        # Check if both files exist
        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            return False
        
        # Check if model is not too old
        model_mtime = datetime.fromtimestamp(os.path.getmtime(model_path))
        age_hours = (datetime.now() - model_mtime).total_seconds() / 3600
        
        if age_hours > self.CACHE_VALIDITY_HOURS:
            return False
        
        return True
    
    def _save_model_to_cache(self, symbol):
        """Save trained model and scaler to cache."""
        if self.model is None:
            return
        
        model_path = self._get_model_path(symbol)
        scaler_path = self._get_scaler_path(symbol)
        
        # Save Keras model
        self.model.save(model_path)
        
        # Save scalers using pickle
        scaler_data = {
            'scaler': self.scaler,
            'close_scaler_min': self.close_scaler.min_,
            'close_scaler_scale': self.close_scaler.scale_,
            'features': self.features
        }
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler_data, f)
        
        print(f"[CACHE] Model saved for {symbol}")
    
    def _load_model_from_cache(self, symbol):
        """
        Load model and scaler from cache.
        
        Returns:
            bool: True if successfully loaded
        """
        model_path = self._get_model_path(symbol)
        scaler_path = self._get_scaler_path(symbol)
        
        try:
            # Load Keras model
            self.model = load_model(model_path)
            
            # Load scalers
            with open(scaler_path, 'rb') as f:
                scaler_data = pickle.load(f)
            
            self.scaler = scaler_data['scaler']
            self.features = scaler_data['features']
            
            # Reconstruct close_scaler
            self.close_scaler = MinMaxScaler(feature_range=(0, 1))
            self.close_scaler.min_ = scaler_data['close_scaler_min']
            self.close_scaler.scale_ = scaler_data['close_scaler_scale']
            
            print(f"[CACHE] Model loaded from cache for {symbol}")
            return True
            
        except Exception as e:
            print(f"[CACHE] Failed to load cache for {symbol}: {e}")
            return False
        
    def load_coin_data(self, symbol):
        """
        Вчитување и подготовка на податоци за одредена криптовалута.
        
        Args:
            symbol: Симбол на криптовалута (пр. BTC-USD)
            
        Returns:
            DataFrame со историски податоци
        """
        # Конвертирање на симбол во формат на фајл
        coin_file = f"{symbol}.json"
        filepath = os.path.join(self.data_dir, coin_file)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Податоците за {symbol} не постојат")
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date').reset_index(drop=True)
        
        # Пополнување на празни вредности
        df = df.ffill().bfill()
        
        return df
    
    def prepare_data(self, df, test_days=180):
        """
        Подготовка на податоци за тренирање и тестирање.
        
        Args:
            df: DataFrame со податоци
            test_days: Број на денови за тестирање
            
        Returns:
            Tuple (train_data, test_data, scaler, close_scaler)
        """
        if self.features[0] not in df.columns:
            # Нема сите потребни колони
            available_features = list(set(self.features) & set(df.columns))
            if 'Close' not in available_features:
                raise ValueError("Close податоците се задолжителни")
            data = df[available_features].values
        else:
            data = df[self.features].values
        
        # Поделба на податоци
        train_data = data[:-test_days]
        test_data = data[-test_days:]
        
        # Нормализација
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaler.fit(train_data)
        
        train_scaled = scaler.transform(train_data)
        test_scaled = scaler.transform(test_data)
        
        # Scaler за Close вредноста (за inverse transform)
        close_scaler = MinMaxScaler(feature_range=(0, 1))
        close_idx = self.features.index('Close')
        close_scaler.min_ = np.array([scaler.min_[close_idx]])
        close_scaler.scale_ = np.array([scaler.scale_[close_idx]])
        
        self.scaler = scaler
        self.close_scaler = close_scaler
        
        return train_scaled, test_scaled, scaler, close_scaler
    
    def create_sequences(self, data):
        """
        Креирање на временски секвенци за LSTM.
        
        Args:
            data: Нормализирани податоци
            
        Returns:
            Tuple (X, y) со секвенци и таргет вредности
        """
        X, y = [], []
        for i in range(len(data) - self.lookback):
            sequence = data[i:i + self.lookback]
            X.append(sequence)
            close_idx = self.features.index('Close')
            y.append(data[i + self.lookback, close_idx])
        
        X = np.array(X)
        y = np.array(y).reshape(-1, 1)
        
        return X, y
    
    def build_model(self, input_shape):
        """
        Креирање на LSTM модел.
        
        Args:
            input_shape: Облик на влезните податоци (lookback, features)
            
        Returns:
            Keras Sequential модел
        """
        model = Sequential()
        
        model.add(LSTM(units=64, return_sequences=True, input_shape=input_shape))
        model.add(Dropout(0.2))
        
        model.add(LSTM(units=64, return_sequences=False))
        model.add(Dropout(0.2))
        
        model.add(Dense(units=25))
        model.add(Dense(units=1))
        
        model.compile(optimizer='adam', loss='mean_squared_error')
        
        return model
    
    def train(self, symbol, epochs=30, batch_size=32, force_retrain=False):
        """
        Тренирање на LSTM моделот со кеширање.
        
        Args:
            symbol: Симбол на криптовалута
            epochs: Број на епохи за тренирање
            batch_size: Големина на batch
            force_retrain: Присилно ретренирање (игнорирај кеш)
            
        Returns:
            Истренираниот модел
        """
        # Check cache first (unless force_retrain is True)
        if not force_retrain and self._is_cache_valid(symbol):
            if self._load_model_from_cache(symbol):
                return self.model
        
        print(f"[TRAIN] Training new model for {symbol}...")
        
        # Вчитување на податоци
        df = self.load_coin_data(symbol)
        
        # Подготовка на податоци
        train_scaled, test_scaled, _, _ = self.prepare_data(df)
        
        # Креирање на секвенци
        X_train, y_train = self.create_sequences(train_scaled)
        X_test, y_test = self.create_sequences(test_scaled)
        
        # Reshape за LSTM
        num_features = X_train.shape[2]
        X_train = np.reshape(X_train, (-1, self.lookback, num_features))
        X_test = np.reshape(X_test, (-1, self.lookback, num_features))
        
        # Креирање и тренирање на модел
        self.model = self.build_model((self.lookback, num_features))
        
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(X_test, y_test),
            verbose=0
        )
        
        # Save to cache after training
        self._save_model_to_cache(symbol)
        
        return self.model
    
    def predict_future(self, symbol, target_date=None, days_ahead=30):
        """
        Предвидување на идни цени со користење на кеширани модели.
        
        Args:
            symbol: Симбол на криптовалута
            target_date: Целен датум за предвидување (datetime или str)
            days_ahead: Број на денови напред за предвидување
            
        Returns:
            Dictionary со предвидувања
        """
        try:
            # Вчитување на податоци
            df = self.load_coin_data(symbol)
            
            # Try to load from cache first, train if needed
            if self.model is None:
                if self._is_cache_valid(symbol):
                    self._load_model_from_cache(symbol)
                else:
                    # Train with full epochs for quality (model will be cached)
                    self.train(symbol, epochs=30)
            
            # If still no model, something went wrong
            if self.model is None:
                raise Exception("Failed to load or train model")
            
            # Подготовка на податоци за предвидување
            # We need fresh scaler if loaded from cache
            if self.scaler is None:
                self.prepare_data(df)
            
            # Get all scaled data
            train_scaled, test_scaled, _, _ = self.prepare_data(df)
            all_data = np.vstack([train_scaled, test_scaled])
            
            # Земање на последните lookback вредности
            last_sequence = all_data[-self.lookback:]
            
            # Предвидување за следните денови
            predictions = []
            current_sequence = last_sequence.copy()
            
            for _ in range(days_ahead):
                # Reshape за LSTM
                input = current_sequence.reshape(1, self.lookback, len(self.features))
                
                # Предвидување
                pred_scaled = self.model.predict(input, verbose=0)[0][0]
                
                # Креирање на нов ред (со предвиденото Close)
                close_idx = self.features.index('Close')
                new_row = current_sequence[-1].copy()
                new_row[close_idx] = pred_scaled
                
                # Додавање во predictions
                predictions.append(pred_scaled)
                
                # Поместување на секвенцата
                current_sequence = np.vstack([current_sequence[1:], new_row])
            
            # Inverse transform на предвидувањата
            predictions_actual = self.close_scaler.inverse_transform(
                np.array(predictions).reshape(-1, 1)
            ).flatten()
            
            # Датуми
            last_date = df['Date'].iloc[-1]
            future_dates = [last_date + timedelta(days=i+1) for i in range(days_ahead)]
            
            # Ако е специфициран target_date, најди го тој датум
            if target_date:
                if isinstance(target_date, str):
                    target_date = datetime.strptime(target_date, '%Y-%m-%d')
                
                # Најди индекс на најблискиот датум
                days_diff = (target_date - last_date).days
                
                if days_diff < 0:
                    raise ValueError("Целниот датум е во минатото")
                elif days_diff >= days_ahead:
                    raise ValueError(f"Целниот датум е премногу далеку (максимум {days_ahead} денови)")
                    
                predicted_price = predictions_actual[days_diff]
                predicted_date = future_dates[days_diff]
            else:
                # Ако нема target_date, земи го првиот ден
                predicted_price = predictions_actual[0]
                predicted_date = future_dates[0]
                days_diff = 0
            
            # Подготовка на историски податоци за график (последните 30 денови)
            historical_days = min(30, len(df))
            historical_dates = df['Date'].iloc[-historical_days:].tolist()
            historical_prices = df['Close'].iloc[-historical_days:].tolist()
            
            # Последна позната цена
            last_price = df['Close'].iloc[-1]
            
            # Насока на промена
            direction = 'UP' if predicted_price > last_price else 'DOWN'
            
            # Подготовка на податоци за график
            chart_labels = [d.strftime('%Y-%m-%d') for d in historical_dates] + [predicted_date.strftime('%Y-%m-%d')]
            chart_values = historical_prices + [float(predicted_price)]
            
            return {
                'predicted_price': float(predicted_price),
                'target_date': predicted_date.strftime('%Y-%m-%d'),
                'last_known_price': float(last_price),
                'direction': direction,
                'days_ahead': days_diff + 1,
                'labels': json.dumps(chart_labels),
                'values': json.dumps(chart_values)
            }
            
        except Exception as e:
            raise Exception(f"Грешка при предвидување: {str(e)}")


def predict_crypto_price(symbol, target_date, data_dir):
    """
    Помагачка функција за предвидување на цена.
    Користи кеширање на модели за побрзи предвидувања.
    
    Args:
        symbol: Симбол на криптовалута (BTC-USD, ETH-USD)
        target_date: Датум за предвидување (YYYY-MM-DD)
        data_dir: Патека до data директориумот
        
    Returns:
        Dictionary со резултати
    """
    predictor = LSTMPredictor(data_dir=data_dir)
    
    # Конвертирање на датум
    if isinstance(target_date, str):
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
    else:
        target_dt = target_date
    
    # Предвидување (ќе користи кеш ако е достапен)
    result = predictor.predict_future(symbol, target_date=target_dt, days_ahead=90)
    
    return result
