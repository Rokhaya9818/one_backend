"""
Module de prédiction avancé avec ARIMA, Prophet et LSTM
Ce module détecte automatiquement si suffisamment de données sont disponibles
et active les modèles appropriés.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import FvrHumain
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Imports conditionnels pour les modèles ML
try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.stattools import adfuller
    ARIMA_AVAILABLE = True
except ImportError:
    ARIMA_AVAILABLE = False

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

try:
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class PredictionModel:
    """Classe de base pour tous les modèles de prédiction"""
    
    def __init__(self, name: str, min_data_points: int):
        self.name = name
        self.min_data_points = min_data_points
        self.is_trained = False
        
    def can_train(self, data_points: int) -> bool:
        """Vérifie si le modèle peut être entraîné avec le nombre de points disponibles"""
        return data_points >= self.min_data_points
    
    def train(self, df: pd.DataFrame):
        """Entraîne le modèle"""
        raise NotImplementedError
    
    def predict(self, periods: int) -> pd.DataFrame:
        """Génère des prédictions"""
        raise NotImplementedError


class LinearExtrapolation(PredictionModel):
    """Extrapolation linéaire simple (modèle actuel)"""
    
    def __init__(self):
        super().__init__("Linear Extrapolation", min_data_points=2)
        self.growth_rate = 0
        self.last_value = 0
        self.last_date = None
        
    def train(self, df: pd.DataFrame):
        """Calcule le taux de croissance"""
        if len(df) < 2:
            self.growth_rate = 0
            self.last_value = df['y'].iloc[-1] if len(df) > 0 else 0
        else:
            # Calcul du taux de croissance moyen
            days_diff = (df['ds'].iloc[-1] - df['ds'].iloc[0]).days
            value_diff = df['y'].iloc[-1] - df['y'].iloc[0]
            self.growth_rate = value_diff / days_diff if days_diff > 0 else 0
            self.last_value = df['y'].iloc[-1]
            
        self.last_date = df['ds'].iloc[-1]
        self.is_trained = True
        
    def predict(self, periods: int) -> pd.DataFrame:
        """Génère des prédictions linéaires"""
        if not self.is_trained:
            raise ValueError("Model not trained")
            
        future_dates = [self.last_date + timedelta(days=i+1) for i in range(periods)]
        predictions = [self.last_value + self.growth_rate * (i+1) for i in range(periods)]
        
        return pd.DataFrame({
            'ds': future_dates,
            'yhat': predictions,
            'yhat_lower': [max(0, p * 0.8) for p in predictions],  # Intervalle -20%
            'yhat_upper': [p * 1.2 for p in predictions]  # Intervalle +20%
        })


class ARIMAModel(PredictionModel):
    """Modèle ARIMA pour prédictions de séries temporelles"""
    
    def __init__(self):
        super().__init__("ARIMA", min_data_points=30)
        self.model = None
        self.fitted_model = None
        self.order = (1, 1, 1)  # Ordre par défaut (p, d, q)
        
    def _check_stationarity(self, series: pd.Series) -> bool:
        """Vérifie la stationnarité avec le test ADF"""
        try:
            result = adfuller(series.dropna())
            # p-value < 0.05 signifie que la série est stationnaire
            return result[1] < 0.05
        except:
            return False
    
    def _find_best_order(self, series: pd.Series) -> Tuple[int, int, int]:
        """Trouve les meilleurs paramètres (p, d, q) pour ARIMA"""
        # Simplifié : teste quelques combinaisons courantes
        best_aic = float('inf')
        best_order = (1, 1, 1)
        
        for p in range(0, 3):
            for d in range(0, 2):
                for q in range(0, 3):
                    try:
                        model = ARIMA(series, order=(p, d, q))
                        fitted = model.fit()
                        if fitted.aic < best_aic:
                            best_aic = fitted.aic
                            best_order = (p, d, q)
                    except:
                        continue
                        
        return best_order
        
    def train(self, df: pd.DataFrame):
        """Entraîne le modèle ARIMA"""
        if not ARIMA_AVAILABLE:
            raise ImportError("statsmodels not installed")
            
        series = df.set_index('ds')['y']
        
        # Trouve les meilleurs paramètres
        self.order = self._find_best_order(series)
        
        # Entraîne le modèle
        self.model = ARIMA(series, order=self.order)
        self.fitted_model = self.model.fit()
        self.is_trained = True
        
    def predict(self, periods: int) -> pd.DataFrame:
        """Génère des prédictions avec ARIMA"""
        if not self.is_trained:
            raise ValueError("Model not trained")
            
        forecast = self.fitted_model.forecast(steps=periods)
        forecast_df = self.fitted_model.get_forecast(steps=periods).summary_frame()
        
        last_date = self.fitted_model.data.dates[-1]
        future_dates = [last_date + timedelta(days=i+1) for i in range(periods)]
        
        return pd.DataFrame({
            'ds': future_dates,
            'yhat': forecast.values,
            'yhat_lower': forecast_df['mean_ci_lower'].values,
            'yhat_upper': forecast_df['mean_ci_upper'].values
        })


class ProphetModel(PredictionModel):
    """Modèle Prophet de Facebook pour prédictions avec saisonnalité"""
    
    def __init__(self):
        super().__init__("Prophet", min_data_points=30)
        self.model = None
        
    def train(self, df: pd.DataFrame):
        """Entraîne le modèle Prophet"""
        if not PROPHET_AVAILABLE:
            raise ImportError("prophet not installed")
            
        # Prophet nécessite les colonnes 'ds' et 'y'
        self.model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=False,  # Pas assez de données pour la saisonnalité annuelle
            interval_width=0.95
        )
        
        self.model.fit(df)
        self.is_trained = True
        
    def predict(self, periods: int) -> pd.DataFrame:
        """Génère des prédictions avec Prophet"""
        if not self.is_trained:
            raise ValueError("Model not trained")
            
        future = self.model.make_future_dataframe(periods=periods)
        forecast = self.model.predict(future)
        
        # Retourne seulement les prédictions futures
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)


class EnsembleModel:
    """Combine plusieurs modèles pour des prédictions plus robustes"""
    
    def __init__(self):
        self.models: List[PredictionModel] = []
        self.weights: List[float] = []
        
    def add_model(self, model: PredictionModel, weight: float = 1.0):
        """Ajoute un modèle à l'ensemble"""
        self.models.append(model)
        self.weights.append(weight)
        
    def train(self, df: pd.DataFrame):
        """Entraîne tous les modèles"""
        for model in self.models:
            if model.can_train(len(df)):
                try:
                    model.train(df)
                except Exception as e:
                    print(f"Erreur lors de l'entraînement de {model.name}: {e}")
                    
    def predict(self, periods: int) -> pd.DataFrame:
        """Génère des prédictions en combinant tous les modèles"""
        predictions = []
        valid_weights = []
        
        for model, weight in zip(self.models, self.weights):
            if model.is_trained:
                try:
                    pred = model.predict(periods)
                    predictions.append(pred)
                    valid_weights.append(weight)
                except Exception as e:
                    print(f"Erreur lors de la prédiction avec {model.name}: {e}")
                    
        if not predictions:
            raise ValueError("Aucun modèle n'a pu générer de prédictions")
            
        # Normalise les poids
        total_weight = sum(valid_weights)
        normalized_weights = [w / total_weight for w in valid_weights]
        
        # Combine les prédictions
        combined = predictions[0].copy()
        combined['yhat'] = sum(pred['yhat'] * w for pred, w in zip(predictions, normalized_weights))
        combined['yhat_lower'] = sum(pred['yhat_lower'] * w for pred, w in zip(predictions, normalized_weights))
        combined['yhat_upper'] = sum(pred['yhat_upper'] * w for pred, w in zip(predictions, normalized_weights))
        
        return combined


def get_time_series_data(db: Session, region: Optional[str] = None) -> pd.DataFrame:
    """Récupère les données de séries temporelles depuis la base"""
    query = db.query(
        FvrHumain.date_bilan,
        func.sum(FvrHumain.cas_confirmes).label('total_cas')
    )
    
    if region:
        query = query.filter(FvrHumain.region == region)
        
    query = query.group_by(FvrHumain.date_bilan).order_by(FvrHumain.date_bilan)
    
    results = query.all()
    
    # Convertit en DataFrame Prophet/ARIMA format
    df = pd.DataFrame([
        {'ds': r.date_bilan, 'y': float(r.total_cas)}
        for r in results
    ])
    
    return df


def select_best_model(db: Session, region: Optional[str] = None) -> PredictionModel:
    """Sélectionne automatiquement le meilleur modèle selon les données disponibles"""
    df = get_time_series_data(db, region)
    data_points = len(df)
    
    print(f"Données disponibles: {data_points} points temporels")
    
    if data_points < 2:
        raise ValueError("Pas assez de données (minimum 2 points)")
    
    # Crée un ensemble de modèles
    ensemble = EnsembleModel()
    
    # Ajoute toujours l'extrapolation linéaire
    linear = LinearExtrapolation()
    ensemble.add_model(linear, weight=1.0)
    
    # Ajoute ARIMA si suffisamment de données
    if data_points >= 30 and ARIMA_AVAILABLE:
        print("✅ ARIMA activé (30+ points)")
        arima = ARIMAModel()
        ensemble.add_model(arima, weight=2.0)  # Poids plus élevé
    else:
        print(f"⏳ ARIMA désactivé (besoin de 30 points, actuellement {data_points})")
    
    # Ajoute Prophet si suffisamment de données
    if data_points >= 30 and PROPHET_AVAILABLE:
        print("✅ Prophet activé (30+ points)")
        prophet = ProphetModel()
        ensemble.add_model(prophet, weight=2.0)  # Poids plus élevé
    else:
        print(f"⏳ Prophet désactivé (besoin de 30 points, actuellement {data_points})")
    
    # Entraîne l'ensemble
    ensemble.train(df)
    
    return ensemble


def generate_advanced_predictions(
    db: Session,
    region: Optional[str] = None,
    periods: int = 30
) -> Dict:
    """Génère des prédictions avec le meilleur modèle disponible"""
    
    # Sélectionne et entraîne le modèle
    model = select_best_model(db, region)
    
    # Génère les prédictions
    predictions = model.predict(periods)
    
    # Prépare le résultat
    result = {
        'region': region or 'National',
        'model_used': [m.name for m in model.models if m.is_trained],
        'data_points': len(get_time_series_data(db, region)),
        'predictions': []
    }
    
    for _, row in predictions.iterrows():
        result['predictions'].append({
            'date': row['ds'].strftime('%Y-%m-%d'),
            'predicted_cases': max(0, int(row['yhat'])),
            'lower_bound': max(0, int(row['yhat_lower'])),
            'upper_bound': int(row['yhat_upper'])
        })
    
    return result


# Fonction de test
if __name__ == "__main__":
    from database import SessionLocal
    
    db = SessionLocal()
    try:
        result = generate_advanced_predictions(db, periods=30)
        print("\n=== RÉSULTAT DES PRÉDICTIONS ===")
        print(f"Région: {result['region']}")
        print(f"Modèles utilisés: {', '.join(result['model_used'])}")
        print(f"Points de données: {result['data_points']}")
        print(f"\nPremières prédictions:")
        for pred in result['predictions'][:7]:
            print(f"  {pred['date']}: {pred['predicted_cases']} cas (intervalle: {pred['lower_bound']}-{pred['upper_bound']})")
    finally:
        db.close()
