# Endpoints pour les corrélations One Health

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from database import get_db
from models import FvrHumain, FvrAnimal, GrippeAviaire, MalariaRegional
import numpy as np
from pydantic import BaseModel

router = APIRouter()

class RegionCorrelation(BaseModel):
    region: str
    fvr_humain: int
    fvr_animal: int
    grippe_aviaire: int
    malaria: int
    risk_level: str  # "faible", "modéré", "élevé", "critique"
    
class CorrelationAlert(BaseModel):
    type: str  # "warning", "danger", "info"
    title: str
    message: str
    region: str
    
class CorrelationSummary(BaseModel):
    total_regions: int
    high_risk_regions: int
    correlation_fvr: float  # Corrélation entre FVR humain et animal
    
@router.get("/api/correlations/by-region", response_model=List[RegionCorrelation])
def get_correlations_by_region(db: Session = Depends(get_db)):
    """Corrélations entre les 3 piliers par région"""
    
    # Récupérer toutes les régions uniques
    regions_query = db.query(FvrHumain.region).filter(
        FvrHumain.region.isnot(None)
    ).distinct()
    
    results = []
    
    for region_row in regions_query:
        region = region_row[0]
        
        # FVR Humain
        fvr_h = db.query(func.sum(FvrHumain.cas_confirmes)).filter(
            FvrHumain.region == region
        ).scalar() or 0
        
        # FVR Animal
        fvr_a = db.query(func.sum(FvrAnimal.cas)).filter(
            FvrAnimal.region == region
        ).scalar() or 0
        
        # Grippe Aviaire
        grippe = db.query(func.sum(GrippeAviaire.cas_confirmes)).filter(
            GrippeAviaire.region == region
        ).scalar() or 0
        
        # Malaria
        malaria = db.query(func.sum(MalariaRegional.cas_confirmes)).filter(
            MalariaRegional.region == region
        ).scalar() or 0
        
        # Calculer le niveau de risque
        total_cases = fvr_h + fvr_a + grippe + (malaria / 1000)  # Normaliser malaria
        
        if total_cases > 1000:
            risk_level = "critique"
        elif total_cases > 500:
            risk_level = "élevé"
        elif total_cases > 100:
            risk_level = "modéré"
        else:
            risk_level = "faible"
        
        results.append(RegionCorrelation(
            region=region,
            fvr_humain=fvr_h,
            fvr_animal=fvr_a,
            grippe_aviaire=grippe,
            malaria=malaria,
            risk_level=risk_level
        ))
    
    return results

@router.get("/api/correlations/alerts", response_model=List[CorrelationAlert])
def get_correlation_alerts(db: Session = Depends(get_db)):
    """Alertes basées sur les corrélations entre piliers"""
    
    alerts = []
    
    # Récupérer toutes les régions uniques
    regions_query = db.query(FvrHumain.region).filter(
        FvrHumain.region.isnot(None)
    ).distinct()
    
    for region_row in regions_query:
        region = region_row[0]
        
        # FVR Humain - requête séparée pour éviter les duplications
        fvr_h = db.query(func.sum(FvrHumain.cas_confirmes)).filter(
            FvrHumain.region == region
        ).scalar() or 0
        
        # FVR Animal - requête séparée pour éviter les duplications
        fvr_a = db.query(func.sum(FvrAnimal.cas)).filter(
            FvrAnimal.region == region
        ).scalar() or 0
        
        # Alerte si FVR Animal élevé et FVR Humain présent
        if fvr_a > 200 and fvr_h > 50:
            alerts.append(CorrelationAlert(
                type="danger",
                title="Risque élevé de transmission animal-humain",
                message=f"À {region} : {fvr_a} cas animaux et {fvr_h} cas humains détectés. Renforcer la surveillance et la vaccination.",
                region=region
            ))
        elif fvr_a > 100 and fvr_h < 10:
            alerts.append(CorrelationAlert(
                type="warning",
                title="Surveillance renforcée recommandée",
                message=f"À {region} : {fvr_a} cas animaux détectés. Risque de transmission aux humains. Prévention recommandée.",
                region=region
            ))
        elif fvr_a > 50 and fvr_h > 50:
            alerts.append(CorrelationAlert(
                type="warning",
                title="Surveillance renforcée recommandée",
                message=f"À {region} : {fvr_a} cas animaux et {fvr_h} cas humains détectés. Risque de transmission. Prévention recommandée.",
                region=region
            ))
    
    # Ajouter des alertes pour les zones à risque multiple
    multi_risk = db.query(
        FvrHumain.region
    ).filter(
        FvrHumain.region.isnot(None)
    ).distinct()
    
    for region_row in multi_risk:
        region = region_row[0]
        
        # Compter les types de maladies présentes
        diseases_count = 0
        
        if db.query(FvrHumain).filter(FvrHumain.region == region, FvrHumain.cas_confirmes > 0).first():
            diseases_count += 1
        if db.query(FvrAnimal).filter(FvrAnimal.region == region, FvrAnimal.cas > 0).first():
            diseases_count += 1
        if db.query(GrippeAviaire).filter(GrippeAviaire.region == region, GrippeAviaire.cas_confirmes > 0).first():
            diseases_count += 1
        
        if diseases_count >= 3:
            alerts.append(CorrelationAlert(
                type="danger",
                title="Zone à risque multiple",
                message=f"{region} présente plusieurs maladies simultanément (FVR, Grippe Aviaire). Coordination One Health nécessaire.",
                region=region
            ))
    
    return alerts

@router.get("/api/correlations/summary", response_model=CorrelationSummary)
def get_correlation_summary(db: Session = Depends(get_db)):
    """Résumé des corrélations One Health"""
    
    # Nombre total de régions
    total_regions = db.query(func.count(func.distinct(FvrHumain.region))).filter(
        FvrHumain.region.isnot(None)
    ).scalar() or 0
    
    # Régions à risque élevé (FVR Humain + Animal)
    high_risk = 0
    regions = db.query(FvrHumain.region).filter(FvrHumain.region.isnot(None)).distinct()
    
    for region_row in regions:
        region = region_row[0]
        fvr_h = db.query(func.sum(FvrHumain.cas_confirmes)).filter(FvrHumain.region == region).scalar() or 0
        fvr_a = db.query(func.sum(FvrAnimal.cas)).filter(FvrAnimal.region == region).scalar() or 0
        
        if fvr_h > 50 and fvr_a > 100:
            high_risk += 1
    
    # Calculer la corrélation FVR (entre FVR Humain et FVR Animal)
    
    # Récupérer les cas FVR Humain et Animal par région
    regions_data = db.query(
        FvrHumain.region,
        func.sum(FvrHumain.cas_confirmes).label('fvr_h'),
        func.sum(FvrAnimal.cas).label('fvr_a')
    ).join(FvrAnimal, FvrHumain.region == FvrAnimal.region).group_by(FvrHumain.region).all()
    
    fvr_h_cases = np.array([d.fvr_h for d in regions_data])
    fvr_a_cases = np.array([d.fvr_a for d in regions_data])
    
    if len(fvr_h_cases) > 1:
        # Calcul de la corrélation de Pearson
        correlation_matrix = np.corrcoef(fvr_h_cases, fvr_a_cases)
        correlation_fvr = correlation_matrix[0, 1]
    else:
        correlation_fvr = 0.0 # Pas assez de données pour calculer la corrélation
    
    return CorrelationSummary(
        total_regions=total_regions,
        high_risk_regions=high_risk,
        correlation_fvr=correlation_fvr
    )
