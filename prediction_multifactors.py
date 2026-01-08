from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, Numeric
from database import get_db
from models import FvrHumain, PollutionAir
from typing import List
from pydantic import BaseModel
from datetime import datetime, timedelta
import math

router = APIRouter()

class RegionPrediction(BaseModel):
    region: str
    current_fvr_cases: int
    predicted_7_days: int
    predicted_14_days: int
    predicted_30_days: int
    pollution_pm25: float
    climate_risk_score: int  # 0-100
    seasonal_risk: str  # Faible, Moyen, Élevé
    combined_risk_score: int  # 0-100
    risk_factors: List[str]
    recommendations: List[str]

class PredictionSummary(BaseModel):
    total_current_cases: int
    predicted_7_days_total: int
    predicted_14_days_total: int
    predicted_30_days_total: int
    high_risk_regions: List[str]
    critical_actions: List[str]

def get_seasonal_risk(month: int) -> tuple:
    """
    Retourne le risque saisonnier selon le mois
    Saison des pluies au Sénégal : Juin-Octobre (plus de moustiques)
    """
    if month in [6, 7, 8, 9, 10]:  # Saison des pluies
        return ("Élevé", 80, "Saison des pluies - Risque accru de transmission vectorielle")
    elif month in [11, 12, 1, 2]:  # Saison sèche froide
        return ("Moyen", 40, "Saison sèche - Risque modéré")
    else:  # Saison sèche chaude
        return ("Faible", 20, "Saison sèche chaude - Risque réduit")

def calculate_climate_risk(month: int) -> int:
    """
    Calcule le score de risque climatique (0-100)
    Basé sur température et humidité typiques du Sénégal
    """
    # Températures moyennes et humidité par mois au Sénégal
    climate_data = {
        1: {"temp": 25, "humidity": 30},  # Janvier
        2: {"temp": 26, "humidity": 35},
        3: {"temp": 28, "humidity": 40},
        4: {"temp": 29, "humidity": 45},
        5: {"temp": 30, "humidity": 55},
        6: {"temp": 31, "humidity": 70},  # Début saison pluies
        7: {"temp": 30, "humidity": 80},
        8: {"temp": 29, "humidity": 85},
        9: {"temp": 29, "humidity": 80},
        10: {"temp": 29, "humidity": 70},  # Fin saison pluies
        11: {"temp": 27, "humidity": 50},
        12: {"temp": 25, "humidity": 35}
    }
    
    data = climate_data.get(month, {"temp": 27, "humidity": 50})
    
    # Score basé sur conditions favorables aux moustiques
    # Température optimale: 25-30°C, Humidité optimale: >60%
    temp_score = 100 if 25 <= data["temp"] <= 30 else max(0, 100 - abs(data["temp"] - 27.5) * 10)
    humidity_score = min(100, data["humidity"] * 1.5)
    
    return int((temp_score + humidity_score) / 2)

@router.get("/api/predictions/regions", response_model=List[RegionPrediction])
def get_region_predictions(db: Session = Depends(get_db)):
    """
    Génère des prédictions par région basées sur FVR, Pollution et Climat
    """
    
    # 1. Récupérer les données FVR actuelles par région
    fvr_data = db.query(
        FvrHumain.region,
        func.sum(FvrHumain.cas_confirmes).label('total_cas')
    ).filter(
        FvrHumain.district.is_(None)
    ).group_by(
        FvrHumain.region
    ).all()
    
    # 2. Récupérer les données de pollution
    # Note: concentration_pm25 est VARCHAR, on doit le convertir en NUMERIC
    recent_pollution = db.query(
        PollutionAir.zone,
        func.avg(func.cast(PollutionAir.concentration_pm25, Numeric)).label('avg_pm25')
    ).filter(
        PollutionAir.annee >= 2020
    ).group_by(
        PollutionAir.zone
    ).all()
    
    pollution_dict = {p.zone: float(p.avg_pm25) if p.avg_pm25 else 50.0 for p in recent_pollution}
    national_pm25 = pollution_dict.get('National', 50.0)
    
    # 3. Obtenir le mois actuel pour le risque saisonnier
    current_month = datetime.now().month
    seasonal_risk, seasonal_score, seasonal_reason = get_seasonal_risk(current_month)
    climate_score = calculate_climate_risk(current_month)
    
    # 4. Calculer les prédictions pour chaque région
    predictions = []
    
    for region_data in fvr_data:
        region = region_data.region
        current_cases = region_data.total_cas
        
        # PM2.5 pour la région
        pm25 = pollution_dict.get(region, national_pm25)
        
        # Calculer le taux de croissance (estimation basée sur les données actuelles)
        # Avec seulement 2 points de données, on utilise une croissance moyenne estimée
        # Taux de croissance hebdomadaire estimé: 10-15% selon les conditions
        
        base_growth_rate = 0.12  # 12% par semaine (estimation conservatrice)
        
        # Ajuster selon les facteurs de risque
        # Pollution élevée augmente le risque de complications respiratoires
        pollution_factor = 1.0 + (pm25 - 50) / 200  # +/- selon pollution
        pollution_factor = max(0.8, min(1.3, pollution_factor))
        
        # Saison des pluies augmente transmission
        seasonal_factor = 1.0 + (seasonal_score / 200)  # 1.0 à 1.4
        
        # Climat favorable augmente transmission
        climate_factor = 1.0 + (climate_score / 300)  # 1.0 à 1.33
        
        # Taux de croissance ajusté
        adjusted_growth = base_growth_rate * pollution_factor * seasonal_factor * climate_factor
        
        # Prédictions
        pred_7_days = int(current_cases * (1 + adjusted_growth))
        pred_14_days = int(current_cases * (1 + adjusted_growth * 2))
        pred_30_days = int(current_cases * (1 + adjusted_growth * 4))
        
        # Score de risque combiné
        # Pondération: FVR 40%, Pollution 20%, Climat 20%, Saison 20%
        fvr_score = min(100, (current_cases / 5))  # Normaliser sur 500 cas max
        pollution_score = min(100, max(0, (pm25 - 15) * 2))  # OMS: <15 bon, >55 mauvais
        
        combined_score = int(
            fvr_score * 0.4 +
            pollution_score * 0.2 +
            climate_score * 0.2 +
            seasonal_score * 0.2
        )
        
        # Identifier les facteurs de risque
        risk_factors = []
        if current_cases > 50:
            risk_factors.append(f"🦠 Nombre élevé de cas FVR ({current_cases})")
        if pm25 > 55:
            risk_factors.append(f"💨 Pollution PM2.5 élevée ({pm25:.1f} µg/m³)")
        if seasonal_score > 60:
            risk_factors.append(f"🌧️ {seasonal_reason}")
        if climate_score > 70:
            risk_factors.append(f"🌡️ Conditions climatiques favorables à la transmission")
        
        # Recommandations
        recommendations = []
        if combined_score > 70:
            recommendations.append("🚨 Renforcement urgent de la surveillance épidémiologique")
            recommendations.append("💉 Campagne de vaccination massive immédiate")
        elif combined_score > 50:
            recommendations.append("⚠️ Surveillance accrue et vaccination préventive")
        
        if pm25 > 55:
            recommendations.append("😷 Distribution de masques anti-pollution")
        
        if seasonal_score > 60:
            recommendations.append("🦟 Intensification de la lutte anti-vectorielle")
            recommendations.append("🏥 Préparation des structures sanitaires")
        
        if not recommendations:
            recommendations.append("✅ Maintien de la surveillance standard")
        
        predictions.append(RegionPrediction(
            region=region,
            current_fvr_cases=current_cases,
            predicted_7_days=pred_7_days,
            predicted_14_days=pred_14_days,
            predicted_30_days=pred_30_days,
            pollution_pm25=round(pm25, 1),
            climate_risk_score=climate_score,
            seasonal_risk=seasonal_risk,
            combined_risk_score=combined_score,
            risk_factors=risk_factors,
            recommendations=recommendations
        ))
    
    # Trier par score de risque décroissant
    predictions.sort(key=lambda x: x.combined_risk_score, reverse=True)
    
    return predictions

@router.get("/api/predictions/summary", response_model=PredictionSummary)
def get_prediction_summary(db: Session = Depends(get_db)):
    """
    Résumé global des prédictions
    """
    
    predictions = get_region_predictions(db)
    
    total_current = sum([p.current_fvr_cases for p in predictions])
    total_7d = sum([p.predicted_7_days for p in predictions])
    total_14d = sum([p.predicted_14_days for p in predictions])
    total_30d = sum([p.predicted_30_days for p in predictions])
    
    high_risk_regions = [p.region for p in predictions if p.combined_risk_score > 60]
    
    # Actions critiques
    critical_actions = []
    if len(high_risk_regions) > 0:
        critical_actions.append(f"🚨 {len(high_risk_regions)} région(s) à haut risque nécessitent une intervention immédiate")
    
    current_month = datetime.now().month
    if current_month in [6, 7, 8, 9, 10]:
        critical_actions.append("🌧️ Saison des pluies: Renforcer la lutte anti-vectorielle dans toutes les régions")
    
    growth_rate = ((total_7d - total_current) / total_current * 100) if total_current > 0 else 0
    if growth_rate > 15:
        critical_actions.append(f"📈 Croissance rapide prévue ({growth_rate:.1f}%): Mobiliser les ressources d'urgence")
    
    if not critical_actions:
        critical_actions.append("✅ Situation sous contrôle - Maintenir la vigilance")
    
    return PredictionSummary(
        total_current_cases=total_current,
        predicted_7_days_total=total_7d,
        predicted_14_days_total=total_14d,
        predicted_30_days_total=total_30d,
        high_risk_regions=high_risk_regions,
        critical_actions=critical_actions
    )
