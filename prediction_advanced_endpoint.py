"""
Endpoint API pour les prédictions avancées avec détection automatique des modèles
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from prediction_advanced import (
    generate_advanced_predictions,
    get_time_series_data,
    select_best_model
)
from typing import Optional, List, Dict
from pydantic import BaseModel

router = APIRouter(prefix="/api/predictions/advanced", tags=["Predictions Advanced"])


class PredictionResponse(BaseModel):
    """Réponse de prédiction"""
    date: str
    predicted_cases: int
    lower_bound: int
    upper_bound: int


class AdvancedPredictionResponse(BaseModel):
    """Réponse complète des prédictions avancées"""
    region: str
    models_used: List[str]
    data_points: int
    models_available: Dict[str, bool]
    predictions: List[PredictionResponse]
    message: str


@router.get("/national", response_model=AdvancedPredictionResponse)
def get_national_predictions(
    periods: int = 30,
    db: Session = Depends(get_db)
):
    """
    Génère des prédictions nationales avec le meilleur modèle disponible
    
    - **periods**: Nombre de jours à prédire (défaut: 30)
    
    Le système sélectionne automatiquement:
    - Linear Extrapolation si < 30 points de données
    - ARIMA + Prophet si >= 30 points de données
    """
    try:
        # Vérifie le nombre de points disponibles
        df = get_time_series_data(db)
        data_points = len(df)
        
        # Génère les prédictions
        result = generate_advanced_predictions(db, region=None, periods=periods)
        
        # Prépare le message informatif
        if data_points < 30:
            message = (
                f"⏳ Utilisation de Linear Extrapolation ({data_points} points disponibles). "
                f"ARIMA et Prophet s'activeront automatiquement à partir de 30 points."
            )
        else:
            message = (
                f"✅ Modèles avancés activés ! ({data_points} points disponibles). "
                f"Prédictions basées sur {', '.join(result['model_used'])}."
            )
        
        return AdvancedPredictionResponse(
            region=result['region'],
            models_used=result['model_used'],
            data_points=data_points,
            models_available={
                'linear': True,
                'arima': data_points >= 30,
                'prophet': data_points >= 30,
                'lstm': data_points >= 100
            },
            predictions=[
                PredictionResponse(**pred) for pred in result['predictions']
            ],
            message=message
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération des prédictions: {str(e)}")


@router.get("/region/{region_name}", response_model=AdvancedPredictionResponse)
def get_region_predictions(
    region_name: str,
    periods: int = 30,
    db: Session = Depends(get_db)
):
    """
    Génère des prédictions pour une région spécifique
    
    - **region_name**: Nom de la région (ex: "Saint-Louis")
    - **periods**: Nombre de jours à prédire (défaut: 30)
    """
    try:
        # Vérifie le nombre de points disponibles pour cette région
        df = get_time_series_data(db, region=region_name)
        data_points = len(df)
        
        if data_points < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Pas assez de données pour la région {region_name} (minimum 2 points requis)"
            )
        
        # Génère les prédictions
        result = generate_advanced_predictions(db, region=region_name, periods=periods)
        
        # Prépare le message informatif
        if data_points < 30:
            message = (
                f"⏳ {region_name}: Utilisation de Linear Extrapolation ({data_points} points). "
                f"Modèles avancés à partir de 30 points."
            )
        else:
            message = (
                f"✅ {region_name}: Modèles avancés activés ({data_points} points). "
                f"Prédictions: {', '.join(result['model_used'])}."
            )
        
        return AdvancedPredictionResponse(
            region=result['region'],
            models_used=result['model_used'],
            data_points=data_points,
            models_available={
                'linear': True,
                'arima': data_points >= 30,
                'prophet': data_points >= 30,
                'lstm': data_points >= 100
            },
            predictions=[
                PredictionResponse(**pred) for pred in result['predictions']
            ],
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/status")
def get_prediction_status(db: Session = Depends(get_db)):
    """
    Retourne le statut des modèles de prédiction disponibles
    """
    try:
        df = get_time_series_data(db)
        data_points = len(df)
        
        return {
            "data_points": data_points,
            "models": {
                "linear": {
                    "available": data_points >= 2,
                    "status": "✅ Actif" if data_points >= 2 else "❌ Inactif",
                    "min_required": 2
                },
                "arima": {
                    "available": data_points >= 30,
                    "status": "✅ Actif" if data_points >= 30 else f"⏳ En attente ({data_points}/30)",
                    "min_required": 30
                },
                "prophet": {
                    "available": data_points >= 30,
                    "status": "✅ Actif" if data_points >= 30 else f"⏳ En attente ({data_points}/30)",
                    "min_required": 30
                },
                "lstm": {
                    "available": data_points >= 100,
                    "status": "✅ Actif" if data_points >= 100 else f"⏳ En attente ({data_points}/100)",
                    "min_required": 100
                }
            },
            "message": (
                f"Actuellement {data_points} points de données disponibles. "
                f"Continuez à importer les communiqués pour activer les modèles avancés !"
            )
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
