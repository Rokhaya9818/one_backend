"""
Script pour ajouter l'endpoint de données cartographiques
À ajouter dans main.py
"""

endpoint_code = '''
# ==================== MAP DATA ENDPOINT ====================

class RegionMapData(BaseModel):
    region: str
    fvr_humain: int
    fvr_animal: int
    grippe_aviaire: int
    total_cases: int

@app.get("/api/dashboard/map-data", response_model=List[RegionMapData])
def get_map_data(db: Session = Depends(get_db)):
    """Données combinées pour la carte du Sénégal"""
    
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
    
    # Combiner toutes les régions
    all_regions = set(fvr_humain_data.keys()) | set(fvr_animal_data.keys()) | set(grippe_aviaire_data.keys())
    
    result = []
    for region in all_regions:
        fvr_h = fvr_humain_data.get(region, 0)
        fvr_a = fvr_animal_data.get(region, 0)
        grippe = grippe_aviaire_data.get(region, 0)
        
        result.append(RegionMapData(
            region=region,
            fvr_humain=fvr_h,
            fvr_animal=fvr_a,
            grippe_aviaire=grippe,
            total_cases=fvr_h + fvr_a + grippe
        ))
    
    # Trier par total décroissant
    result.sort(key=lambda x: x.total_cases, reverse=True)
    
    return result
'''

print(endpoint_code)
