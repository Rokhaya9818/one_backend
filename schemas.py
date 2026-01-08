from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List

# Schémas pour Malaria
class MalariaBase(BaseModel):
    indicator_code: str
    indicator_name: str
    year: int
    value: Optional[str] = None
    numeric_value: Optional[str] = None
    low_value: Optional[str] = None
    high_value: Optional[str] = None

class MalariaResponse(MalariaBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schémas pour Tuberculose
class TuberculoseBase(BaseModel):
    indicator_code: str
    indicator_name: str
    year: int
    value: Optional[str] = None
    numeric_value: Optional[str] = None
    low_value: Optional[str] = None
    high_value: Optional[str] = None

class TuberculoseResponse(TuberculoseBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schémas pour FVR Humain
class FvrHumainBase(BaseModel):
    date_bilan: date
    cas_confirmes: int = 0
    deces: int = 0
    gueris: int = 0
    region: Optional[str] = None
    district: Optional[str] = None
    taux_letalite: Optional[str] = None

class FvrHumainResponse(FvrHumainBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schémas pour FVR Animal
class FvrAnimalBase(BaseModel):
    annee: int
    cas: int = 0
    espece: Optional[str] = None
    region: Optional[str] = None
    localisation: Optional[str] = None
    source: Optional[str] = None

class FvrAnimalResponse(FvrAnimalBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schémas pour Grippe Aviaire
class GrippeAviaireBase(BaseModel):
    report_id: str
    date_rapport: date
    region: Optional[str] = None
    espece: Optional[str] = None
    maladie: Optional[str] = None
    cas_confirmes: int = 0
    deces: int = 0
    statut_epidemie: Optional[str] = None

class GrippeAviaireResponse(GrippeAviaireBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schémas pour Pollution Air
class PollutionAirBase(BaseModel):
    annee: int
    zone: str
    concentration_pm25: Optional[str] = None

class PollutionAirResponse(PollutionAirBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schémas pour Régions
class RegionBase(BaseModel):
    nom: str
    code: str
    latitude: Optional[str] = None
    longitude: Optional[str] = None

class RegionResponse(RegionBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schémas pour les KPIs du Dashboard
class DashboardKPIs(BaseModel):
    malaria_cases: str
    tuberculose_cases: str
    fvr_humain_cases: int
    fvr_humain_deces: int
    fvr_humain_gueris: int
    fvr_animal_cases: int
    grippe_aviaire_cases: int
    pm25_recent: str
    taux_letalite_fvr: float

class RegionStat(BaseModel):
    region: str
    total: int

class IndicatorStat(BaseModel):
    name: str
    value: int
