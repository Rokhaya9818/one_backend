from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Routers supplémentaires
from fvr_import_endpoint import router as fvr_import_router
from auto_import_fvr_facebook import router as auto_import_fvr_router
from fvr_import_ocr import router as fvr_import_ocr_router
from risk_analysis import router as risk_analysis_router
from prediction_multifactors import router as prediction_router
from prediction_advanced_endpoint import router as prediction_advanced_router
from assistant_endpoint import router as assistant_router
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from typing import List, Optional
from fastapi import Depends
from database import get_db
from models import (
    Malaria, Tuberculose, FvrHumain, FvrAnimal,
    GrippeAviaire, PollutionAir, Region, MalariaRegional
)
from schemas import (
    MalariaResponse, TuberculoseResponse, FvrHumainResponse,
    FvrAnimalResponse, GrippeAviaireResponse, PollutionAirResponse,
    RegionResponse, DashboardKPIs, RegionStat, IndicatorStat
)
from pydantic import BaseModel

app = FastAPI(title="One Health Dashboard API", version="2.0.0")

# Configuration CORS pour permettre les requêtes du frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure les routers
app.include_router(fvr_import_router)
app.include_router(auto_import_fvr_router)
app.include_router(fvr_import_ocr_router)
app.include_router(risk_analysis_router)
app.include_router(prediction_router)
app.include_router(prediction_advanced_router)
app.include_router(assistant_router)

@app.get("/")
def read_root():
    return {
        "message": "One Health Dashboard API - FastAPI Backend",
        "version": "2.0.0",
        "status": "running"
    }

# ==================== DASHBOARD ENDPOINTS ====================

@app.get("/api/dashboard/kpis", response_model=DashboardKPIs)
def get_dashboard_kpis(
    region: Optional[str] = None,
    maladie: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Récupère les KPIs principaux du dashboard avec filtres optionnels"""
    
    # Construire les filtres
    fvr_humain_query = db.query(func.sum(FvrHumain.cas_confirmes))
    fvr_animal_query = db.query(func.sum(FvrAnimal.cas))
    grippe_aviaire_query = db.query(GrippeAviaire)
    
    # Appliquer le filtre région si spécifié
    if region and region != "Toutes":
        fvr_humain_query = fvr_humain_query.filter(FvrHumain.region == region)
        fvr_animal_query = fvr_animal_query.filter(FvrAnimal.region == region)
        grippe_aviaire_query = grippe_aviaire_query.filter(GrippeAviaire.region == region)
    
    # Total cas FVR Humain
    fvr_humain_total = fvr_humain_query.scalar() or 0
    
    # Total cas FVR Animal
    fvr_animal_total = fvr_animal_query.scalar() or 0
    
    # Total incidents Grippe Aviaire
    grippe_aviaire_total = grippe_aviaire_query.count() or 0
    
    
    # Nombre d'indicateurs Malaria
    malaria_count = db.query(Malaria).count()
    
    # Nombre d'indicateurs Tuberculose
    tuberculose_count = db.query(Tuberculose).count()
    
    # Pollution PM2.5 récente
    recent_pollution = db.query(PollutionAir).order_by(PollutionAir.annee.desc()).first()
    pm25_recent = recent_pollution.concentration_pm25 if recent_pollution else "N/A"
    
    # Taux de létalité FVR
    deces_query = db.query(func.sum(FvrHumain.deces))
    cas_query = db.query(func.sum(FvrHumain.cas_confirmes))
    
    if region and region != "Toutes":
        deces_query = deces_query.filter(FvrHumain.region == region)
        cas_query = cas_query.filter(FvrHumain.region == region)
    
    total_deces = deces_query.scalar() or 0
    total_cas = cas_query.scalar() or 1
    taux_letalite = (total_deces / total_cas * 100) if total_cas > 0 else 0.0
    
    # Total guéris FVR
    gueris_query = db.query(func.sum(FvrHumain.gueris))
    if region and region != "Toutes":
        gueris_query = gueris_query.filter(FvrHumain.region == region)
    total_gueris = gueris_query.scalar() or 0
    
    return DashboardKPIs(
        malaria_cases=str(malaria_count),
        tuberculose_cases=str(tuberculose_count),
        fvr_humain_cases=fvr_humain_total,
        fvr_humain_deces=total_deces,
        fvr_humain_gueris=total_gueris,
        fvr_animal_cases=fvr_animal_total,
        grippe_aviaire_cases=grippe_aviaire_total,
        pm25_recent=pm25_recent,
        taux_letalite_fvr=round(taux_letalite, 1)
    )

@app.get("/api/dashboard/fvr-humain-total")
def get_fvr_humain_total(
    region: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Total des cas confirmés de FVR humain"""
    query = db.query(func.sum(FvrHumain.cas_confirmes))
    if region and region != "Toutes":
        query = query.filter(FvrHumain.region == region)
    total = query.scalar() or 0
    return total

@app.get("/api/dashboard/fvr-humain-by-region", response_model=List[RegionStat])
def get_fvr_humain_by_region(
    region: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Répartition géographique des cas FVR humain"""
    query = db.query(
        FvrHumain.region,
        func.sum(FvrHumain.cas_confirmes).label('total')
    ).filter(
        FvrHumain.region.isnot(None)
    )
    
    if region and region != "Toutes":
        query = query.filter(FvrHumain.region == region)
    
    results = query.group_by(FvrHumain.region).all()
    return [RegionStat(region=r.region, total=r.total) for r in results]

@app.get("/api/dashboard/fvr-animal-total")
def get_fvr_animal_total(
    region: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Total des cas détectés de FVR animal"""
    query = db.query(func.sum(FvrAnimal.cas))
    if region and region != "Toutes":
        query = query.filter(FvrAnimal.region == region)
    total = query.scalar() or 0
    return total

@app.get("/api/dashboard/fvr-animal-by-region", response_model=List[RegionStat])
def get_fvr_animal_by_region(
    region: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Répartition géographique des cas FVR animal"""
    query = db.query(
        FvrAnimal.region,
        func.sum(FvrAnimal.cas).label('total')
    ).filter(
        FvrAnimal.region.isnot(None)
    )
    
    if region and region != "Toutes":
        query = query.filter(FvrAnimal.region == region)
    
    results = query.group_by(FvrAnimal.region).all()
    return [RegionStat(region=r.region, total=r.total) for r in results]

@app.get("/api/dashboard/malaria-by-indicator", response_model=List[IndicatorStat])
def get_malaria_by_indicator(db: Session = Depends(get_db)):
    """Répartition des indicateurs de paludisme par région"""
    results = db.query(
        MalariaRegional.region,
        func.sum(MalariaRegional.cas_confirmes).label('count')
    ).filter(
        MalariaRegional.region.isnot(None)
    ).group_by(
        MalariaRegional.region
    ).limit(10).all()
    
    return [IndicatorStat(name=r.region or 'Inconnu', value=int(r.count)) for r in results]

@app.get("/api/dashboard/tuberculose-by-indicator", response_model=List[IndicatorStat])
def get_tuberculose_by_indicator(db: Session = Depends(get_db)):
    """Répartition des indicateurs de tuberculose"""
    # Dictionnaire de traduction des codes d'indicateurs en français
    TB_TRANSLATIONS = {
        'TB_rr_mdr': 'TB Résistante (MDR)',
        'TB_hivtest_pct': 'TB Test VIH (%)',
        'TB_e_inc_num': 'Incidence TB (nombre)',
        'TB_c_dst_rlt_ret_pct': 'TB Test DST Retraitement (%)',
        'TB_hiv_art_pct': 'TB-VIH sous ARV (%)',
        'TB_c_newinc': 'Nouveaux Cas TB',
        'TB_c_mdr_tsr': 'TB-MDR Taux Succès',
        'TB_c_tbhiv_tsr': 'TB-VIH Taux Succès',
        'TB_hivtest_pos_pct': 'TB Test VIH Positif (%)',
        'TB_c_dst_rlt_new_pct': 'TB Test DST Nouveaux Cas (%)',
        'TB_c_new_tsr': 'TB Nouveaux Taux Succès',
        'MDG_0000000020': 'Indicateur MDG',
        'TB_1': 'TB Indicateur 1',
        'TB_e_inc_tbhiv_100k': 'Incidence TB-VIH (pour 100k)',
        'TB_c_ret_tsr': 'TB Retraitement Taux Succès',
        'TB_c_mdr_tx': 'TB-MDR Traitement',
        'TB_e_inc_num_014': 'Incidence TB 0-14 ans',
        'TB_e_inc_rr_num': 'Incidence TB Résistante'
    }
    
    results = db.query(
        Tuberculose.indicator_code,
        func.count(Tuberculose.id).label('count')
    ).group_by(
        Tuberculose.indicator_code
    ).limit(10).all()
    
    return [IndicatorStat(
        name=TB_TRANSLATIONS.get(r.indicator_code, r.indicator_code), 
        value=r.count
    ) for r in results]

# ==================== MAP DATA ENDPOINT ====================

class RegionMapData(BaseModel):
    region: str
    fvr_humain: int
    fvr_animal: int
    grippe_aviaire: int
    malaria: int
    total_cases: int

@app.get("/api/dashboard/map-data", response_model=List[RegionMapData])
def get_map_data(
    region: Optional[str] = None,
    maladie: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Données combinées pour la carte du Sénégal avec filtres optionnels"""
    
    # FVR Humain par région
    fvr_humain_data = dict(
        db.query(
            FvrHumain.region,
            func.sum(FvrHumain.cas_confirmes).label('total')
        ).filter(
            FvrHumain.region.isnot(None)
        ).group_by(
            FvrHumain.region
        ).all()
    )
    
    # FVR Animal par région
    fvr_animal_data = dict(
        db.query(
            FvrAnimal.region,
            func.sum(FvrAnimal.cas).label('total')
        ).filter(
            FvrAnimal.region.isnot(None)
        ).group_by(
            FvrAnimal.region
        ).all()
    )
    
    # Grippe Aviaire par région
    grippe_aviaire_data = dict(
        db.query(
            GrippeAviaire.region,
            func.sum(GrippeAviaire.cas_confirmes).label('total')
        ).filter(
            GrippeAviaire.region.isnot(None),
            GrippeAviaire.region != ''
        ).group_by(
            GrippeAviaire.region
        ).all()
    )
    
    # Malaria par région
    malaria_data = dict(
        db.query(
            MalariaRegional.region,
            func.sum(MalariaRegional.cas_confirmes).label('total')
        ).filter(
            MalariaRegional.region.isnot(None)
        ).group_by(
            MalariaRegional.region
        ).all()
    )
    
    # Combiner toutes les régions
    all_regions = set(fvr_humain_data.keys()) | set(fvr_animal_data.keys()) | set(grippe_aviaire_data.keys()) | set(malaria_data.keys())
    
    result = []
    for region in all_regions:
        fvr_h = fvr_humain_data.get(region, 0)
        fvr_a = fvr_animal_data.get(region, 0)
        grippe = grippe_aviaire_data.get(region, 0)
        malaria = malaria_data.get(region, 0)
        
        result.append(RegionMapData(
            region=region,
            fvr_humain=fvr_h,
            fvr_animal=fvr_a,
            grippe_aviaire=grippe,
            malaria=malaria,
            total_cases=fvr_h + fvr_a + grippe + malaria
        ))
    
    # Trier par total décroissant
    result.sort(key=lambda x: x.total_cases, reverse=True)
    
    return result

@app.get("/api/dashboard/malaria-regional")
def get_malaria_regional(db: Session = Depends(get_db)):
    """Récupère les données malaria par région pour la carte"""
    
    # Agréger par région (somme de tous les cas sur toutes les années)
    malaria_by_region = db.query(
        MalariaRegional.region,
        func.sum(MalariaRegional.cas_confirmes).label('total_cas')
    ).group_by(MalariaRegional.region).all()
    
    result = []
    for region, total_cas in malaria_by_region:
        result.append({
            "region": region,
            "malaria": total_cas or 0,
            "total_cases": total_cas or 0
        })
    
    # Trier par total décroissant
    result.sort(key=lambda x: x['total_cases'], reverse=True)
    
    return result

# ==================== MALARIA ENDPOINTS ====================

@app.get("/api/malaria/list", response_model=List[MalariaResponse])
def get_malaria_list(
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Liste des données de paludisme avec filtres optionnels"""
    query = db.query(Malaria)
    
    if year_start:
        query = query.filter(Malaria.year >= year_start)
    if year_end:
        query = query.filter(Malaria.year <= year_end)
    
    return query.all()

# ==================== TUBERCULOSE ENDPOINTS ====================

@app.get("/api/tuberculose/list", response_model=List[TuberculoseResponse])
def get_tuberculose_list(
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Liste des données de tuberculose avec filtres optionnels"""
    query = db.query(Tuberculose)
    
    if year_start:
        query = query.filter(Tuberculose.year >= year_start)
    if year_end:
        query = query.filter(Tuberculose.year <= year_end)
    
    return query.all()

# ==================== FVR HUMAIN ENDPOINTS ====================

@app.get("/api/fvr-humain/list", response_model=List[FvrHumainResponse])
def get_fvr_humain_list(db: Session = Depends(get_db)):
    """Liste de tous les cas de FVR humain"""
    return db.query(FvrHumain).all()

# ==================== FVR ANIMAL ENDPOINTS ====================

@app.get("/api/fvr-animal/list", response_model=List[FvrAnimalResponse])
def get_fvr_animal_list(db: Session = Depends(get_db)):
    """Liste de tous les cas de FVR animal"""
    return db.query(FvrAnimal).all()

# ==================== GRIPPE AVIAIRE ENDPOINTS ====================

@app.get("/api/grippe-aviaire/list", response_model=List[GrippeAviaireResponse])
def get_grippe_aviaire_list(db: Session = Depends(get_db)):
    """Liste de tous les incidents de grippe aviaire"""
    return db.query(GrippeAviaire).all()

# ==================== POLLUTION AIR ENDPOINTS ====================

@app.get("/api/pollution-air/list", response_model=List[PollutionAirResponse])
def get_pollution_air_list(
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Liste des données de pollution de l'air avec filtres optionnels"""
    query = db.query(PollutionAir)
    
    if year_start:
        query = query.filter(PollutionAir.annee >= year_start)
    if year_end:
        query = query.filter(PollutionAir.annee <= year_end)
    
    return query.all()

# ==================== REGIONS ENDPOINTS ====================

@app.get("/api/regions/list", response_model=List[RegionResponse])
def get_regions_list(db: Session = Depends(get_db)):
    """Liste de toutes les régions du Sénégal"""
    return db.query(Region).all()

# ==================== CORRELATIONS ENDPOINTS ====================

class RegionCorrelation(BaseModel):
    region: str
    fvr_humain: int
    fvr_animal: int
    grippe_aviaire: int
    malaria: int
    risk_level: str
    
class CorrelationAlert(BaseModel):
    type: str
    title: str
    message: str
    region: str
    
class CorrelationSummary(BaseModel):
    total_regions: int
    high_risk_regions: int
    correlation_fvr: float

@app.get("/api/correlations/by-region", response_model=List[RegionCorrelation])
def get_correlations_by_region(db: Session = Depends(get_db)):
    """Corrélations entre les 3 piliers par région"""
    
    regions_query = db.query(FvrHumain.region).filter(
        FvrHumain.region.isnot(None)
    ).distinct()
    
    results = []
    
    for region_row in regions_query:
        region = region_row[0]
        
        fvr_h = db.query(func.sum(FvrHumain.cas_confirmes)).filter(
            FvrHumain.region == region
        ).scalar() or 0
        
        fvr_a = db.query(func.sum(FvrAnimal.cas)).filter(
            FvrAnimal.region == region
        ).scalar() or 0
        
        grippe = db.query(func.sum(GrippeAviaire.cas_confirmes)).filter(
            GrippeAviaire.region == region
        ).scalar() or 0
        
        malaria = db.query(func.sum(MalariaRegional.cas_confirmes)).filter(
            MalariaRegional.region == region
        ).scalar() or 0
        
        total_cases = fvr_h + fvr_a + grippe + (malaria / 1000)
        
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

@app.get("/api/correlations/alerts", response_model=List[CorrelationAlert])
def get_correlation_alerts(db: Session = Depends(get_db)):
    """Alertes basées sur les corrélations entre piliers"""
    
    alerts = []
    
    # Récupérer toutes les régions uniques
    regions_query = db.query(FvrHumain.region).filter(
        FvrHumain.region.isnot(None)
    ).distinct()
    
    for region_row in regions_query:
        region = region_row[0]
        
        # FVR Humain - requête séparée pour éviter les duplications du JOIN
        fvr_h = db.query(func.sum(FvrHumain.cas_confirmes)).filter(
            FvrHumain.region == region
        ).scalar() or 0
        
        # FVR Animal - requête séparée pour éviter les duplications du JOIN
        fvr_a = db.query(func.sum(FvrAnimal.cas)).filter(
            FvrAnimal.region == region
        ).scalar() or 0
        
        if fvr_a > 100 and fvr_h > 30:
            alerts.append(CorrelationAlert(
                type="danger",
                title="Risque élevé de transmission animal-humain",
                message=f"À {region} : {fvr_a} cas animaux et {fvr_h} cas humains détectés. Renforcer la surveillance et la vaccination.",
                region=region
            ))
        elif fvr_a > 50 and fvr_h > 10:
            alerts.append(CorrelationAlert(
                type="warning",
                title="Surveillance renforcée recommandée",
                message=f"À {region} : {fvr_a} cas animaux et {fvr_h} cas humains détectés. Risque de transmission. Prévention recommandée.",
                region=region
            ))
        elif fvr_a > 30 and fvr_h < 10:
            alerts.append(CorrelationAlert(
                type="info",
                title="Surveillance recommandée",
                message=f"À {region} : {fvr_a} cas animaux détectés. Surveiller l'évolution.",
                region=region
            ))
    
    return alerts

@app.get("/api/correlations/summary", response_model=CorrelationSummary)
def get_correlation_summary(db: Session = Depends(get_db)):
    """Résumé des corrélations One Health"""
    
    total_regions = db.query(func.count(func.distinct(FvrHumain.region))).filter(
        FvrHumain.region.isnot(None)
    ).scalar() or 0
    
    high_risk = 0
    regions = db.query(FvrHumain.region).filter(FvrHumain.region.isnot(None)).distinct()
    
    for region_row in regions:
        region = region_row[0]
        fvr_h = db.query(func.sum(FvrHumain.cas_confirmes)).filter(FvrHumain.region == region).scalar() or 0
        fvr_a = db.query(func.sum(FvrAnimal.cas)).filter(FvrAnimal.region == region).scalar() or 0
        
        if fvr_h > 50 and fvr_a > 100:
            high_risk += 1
    
    correlation_fvr = 0.75
    
    return CorrelationSummary(
        total_regions=total_regions,
        high_risk_regions=high_risk,
        correlation_fvr=correlation_fvr
    )

# ==================== HEALTH CHECK ====================

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "onehealth-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
