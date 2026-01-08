from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import FvrHumain, PollutionAir
from typing import List
from pydantic import BaseModel

router = APIRouter()

class RegionRiskScore(BaseModel):
    region: str
    fvr_cases: int
    fvr_deaths: int
    lethality_rate: float
    pollution_pm25: float
    fvr_risk_score: int  # 0-100
    pollution_risk_score: int  # 0-100
    combined_risk_score: int  # 0-100
    risk_level: str  # Faible, Moyen, Élevé, Critique
    priority: int  # 1-4 (1 = plus prioritaire)

class ResourceRecommendation(BaseModel):
    region: str
    risk_level: str
    vaccines_needed: int
    hospital_beds_needed: int
    medical_staff_needed: int
    air_purifiers_needed: int
    actions: List[str]

@router.get("/api/risk-analysis/regions", response_model=List[RegionRiskScore])
def get_region_risk_scores(db: Session = Depends(get_db)):
    """
    Calcule le score de risque pour chaque région basé sur FVR et Pollution
    """
    
    # 1. Récupérer les données FVR par région
    fvr_data = db.query(
        FvrHumain.region,
        func.sum(FvrHumain.cas_confirmes).label('total_cas'),
        func.sum(FvrHumain.deces).label('total_deces')
    ).filter(
        FvrHumain.district.is_(None)
    ).group_by(
        FvrHumain.region
    ).all()
    
    # 2. Récupérer les données de pollution récentes
    recent_pollution = db.query(
        PollutionAir.zone,
        func.avg(PollutionAir.concentration_pm25).label('avg_pm25')
    ).filter(
        PollutionAir.annee >= 2020  # Données récentes
    ).group_by(
        PollutionAir.zone
    ).all()
    
    pollution_dict = {p.zone: float(p.avg_pm25) if p.avg_pm25 else 0 for p in recent_pollution}
    
    # Si pas de données par région, utiliser la moyenne nationale
    national_pm25 = pollution_dict.get('National', 50.0)
    
    # 3. Calculer les scores de risque
    results = []
    max_fvr_cases = max([f.total_cas for f in fvr_data]) if fvr_data else 1
    
    for region_data in fvr_data:
        region = region_data.region
        cas = region_data.total_cas
        deces = region_data.total_deces
        
        # Taux de létalité
        lethality_rate = (deces / cas * 100) if cas > 0 else 0
        
        # PM2.5 pour la région (ou national si pas de données régionales)
        pm25 = pollution_dict.get(region, national_pm25)
        
        # Score FVR (0-100) basé sur nombre de cas et létalité
        fvr_score = min(100, int((cas / max_fvr_cases) * 70 + lethality_rate * 3))
        
        # Score Pollution (0-100) basé sur PM2.5
        # OMS recommande < 15 µg/m³, dangereux > 55 µg/m³
        if pm25 < 15:
            pollution_score = 10
        elif pm25 < 35:
            pollution_score = 30
        elif pm25 < 55:
            pollution_score = 60
        else:
            pollution_score = min(100, int(55 + (pm25 - 55) / 2))
        
        # Score combiné (moyenne pondérée: FVR 70%, Pollution 30%)
        combined_score = int(fvr_score * 0.7 + pollution_score * 0.3)
        
        # Niveau de risque
        if combined_score < 25:
            risk_level = "Faible"
            priority = 4
        elif combined_score < 50:
            risk_level = "Moyen"
            priority = 3
        elif combined_score < 75:
            risk_level = "Élevé"
            priority = 2
        else:
            risk_level = "Critique"
            priority = 1
        
        results.append(RegionRiskScore(
            region=region,
            fvr_cases=cas,
            fvr_deaths=deces,
            lethality_rate=round(lethality_rate, 1),
            pollution_pm25=round(pm25, 1),
            fvr_risk_score=fvr_score,
            pollution_risk_score=pollution_score,
            combined_risk_score=combined_score,
            risk_level=risk_level,
            priority=priority
        ))
    
    # Trier par priorité (1 = plus prioritaire)
    results.sort(key=lambda x: x.priority)
    
    return results

@router.get("/api/risk-analysis/recommendations", response_model=List[ResourceRecommendation])
def get_resource_recommendations(db: Session = Depends(get_db)):
    """
    Génère des recommandations d'allocation de ressources par région
    """
    
    # Récupérer les scores de risque
    risk_scores = get_region_risk_scores(db)
    
    recommendations = []
    
    for risk in risk_scores:
        # Calculer les besoins en ressources
        # Formule: besoins proportionnels aux cas et au niveau de risque
        
        # Vaccins: 2 doses par cas + 20% buffer + bonus si risque élevé
        vaccines = int(risk.fvr_cases * 2 * 1.2)
        if risk.risk_level in ["Élevé", "Critique"]:
            vaccines = int(vaccines * 1.5)
        
        # Lits d'hôpital: 10% des cas (estimation taux hospitalisation)
        beds = max(1, int(risk.fvr_cases * 0.1))
        if risk.risk_level == "Critique":
            beds = int(beds * 1.5)
        
        # Personnel médical: 1 pour 20 cas
        staff = max(1, int(risk.fvr_cases / 20))
        if risk.risk_level in ["Élevé", "Critique"]:
            staff = int(staff * 1.3)
        
        # Purificateurs d'air si pollution élevée
        purifiers = 0
        if risk.pollution_pm25 > 55:
            purifiers = int(risk.fvr_cases / 10)  # 1 pour 10 cas
        
        # Actions recommandées
        actions = []
        
        if risk.risk_level == "Critique":
            actions.append("🚨 URGENCE: Déploiement immédiat d'équipes médicales")
            actions.append("💉 Campagne de vaccination massive prioritaire")
            actions.append("🏥 Augmentation capacité hospitalière")
        elif risk.risk_level == "Élevé":
            actions.append("⚠️ Surveillance renforcée")
            actions.append("💉 Vaccination accélérée")
            actions.append("📢 Sensibilisation communautaire intensive")
        elif risk.risk_level == "Moyen":
            actions.append("👁️ Surveillance continue")
            actions.append("💉 Vaccination préventive")
        else:
            actions.append("✅ Maintien surveillance standard")
        
        if risk.pollution_pm25 > 55:
            actions.append("😷 Distribution de masques anti-pollution")
            actions.append("🌬️ Installation de purificateurs d'air")
        
        if risk.lethality_rate > 5:
            actions.append("🏥 Renforcement soins intensifs")
            actions.append("👨‍⚕️ Formation personnel gestion cas graves")
        
        recommendations.append(ResourceRecommendation(
            region=risk.region,
            risk_level=risk.risk_level,
            vaccines_needed=vaccines,
            hospital_beds_needed=beds,
            medical_staff_needed=staff,
            air_purifiers_needed=purifiers,
            actions=actions
        ))
    
    return recommendations

@router.get("/api/risk-analysis/summary")
def get_risk_summary(db: Session = Depends(get_db)):
    """
    Résumé global de l'analyse des risques
    """
    
    risk_scores = get_region_risk_scores(db)
    recommendations = get_resource_recommendations(db)
    
    # Statistiques globales
    total_regions = len(risk_scores)
    critical_regions = len([r for r in risk_scores if r.risk_level == "Critique"])
    high_risk_regions = len([r for r in risk_scores if r.risk_level == "Élevé"])
    medium_risk_regions = len([r for r in risk_scores if r.risk_level == "Moyen"])
    low_risk_regions = len([r for r in risk_scores if r.risk_level == "Faible"])
    
    # Besoins totaux
    total_vaccines = sum([r.vaccines_needed for r in recommendations])
    total_beds = sum([r.hospital_beds_needed for r in recommendations])
    total_staff = sum([r.medical_staff_needed for r in recommendations])
    total_purifiers = sum([r.air_purifiers_needed for r in recommendations])
    
    # Régions prioritaires
    priority_regions = [r.region for r in risk_scores if r.priority <= 2]
    
    return {
        "total_regions_analyzed": total_regions,
        "risk_distribution": {
            "critical": critical_regions,
            "high": high_risk_regions,
            "medium": medium_risk_regions,
            "low": low_risk_regions
        },
        "total_resource_needs": {
            "vaccines": total_vaccines,
            "hospital_beds": total_beds,
            "medical_staff": total_staff,
            "air_purifiers": total_purifiers
        },
        "priority_regions": priority_regions,
        "overall_risk_level": "Critique" if critical_regions > 0 else "Élevé" if high_risk_regions > 0 else "Moyen"
    }
