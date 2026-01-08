import json
import sys
from datetime import datetime, date
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import (
    Malaria, Tuberculose, FvrHumain, FvrAnimal,
    GrippeAviaire, PollutionAir, Region, Base
)

def parse_date(date_str):
    """Parse date string to date object"""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
    except:
        return None

def parse_datetime(dt_str):
    """Parse datetime string to datetime object"""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except:
        return None

def import_data_from_json(json_file_path: str):
    """Import data from JSON export file"""
    
    print(f"📂 Chargement du fichier JSON: {json_file_path}")
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    db = SessionLocal()
    
    try:
        # Import Malaria
        if 'malaria' in data:
            print(f"\n📊 Import des données Paludisme...")
            malaria_count = 0
            for item in data['malaria']:
                malaria = Malaria(
                    indicator_code=item['indicatorCode'],
                    indicator_name=item['indicatorName'],
                    year=item['year'],
                    value=item.get('value'),
                    numeric_value=item.get('numericValue'),
                    low_value=item.get('lowValue'),
                    high_value=item.get('highValue'),
                    created_at=parse_datetime(item.get('createdAt')) or datetime.now()
                )
                db.add(malaria)
                malaria_count += 1
            db.commit()
            print(f"✅ {malaria_count} enregistrements Paludisme importés")
        
        # Import Tuberculose
        if 'tuberculose' in data:
            print(f"\n📊 Import des données Tuberculose...")
            tb_count = 0
            for item in data['tuberculose']:
                tuberculose = Tuberculose(
                    indicator_code=item['indicatorCode'],
                    indicator_name=item['indicatorName'],
                    year=item['year'],
                    value=item.get('value'),
                    numeric_value=item.get('numericValue'),
                    low_value=item.get('lowValue'),
                    high_value=item.get('highValue'),
                    created_at=parse_datetime(item.get('createdAt')) or datetime.now()
                )
                db.add(tuberculose)
                tb_count += 1
            db.commit()
            print(f"✅ {tb_count} enregistrements Tuberculose importés")
        
        # Import FVR Humain
        if 'fvrHumain' in data:
            print(f"\n📊 Import des données FVR Humain...")
            fvr_h_count = 0
            for item in data['fvrHumain']:
                fvr_humain = FvrHumain(
                    date_bilan=parse_date(item['dateBilan']),
                    cas_confirmes=item.get('casConfirmes', 0),
                    deces=item.get('deces', 0),
                    gueris=item.get('gueris', 0),
                    region=item.get('region'),
                    district=item.get('district'),
                    taux_letalite=item.get('tauxLetalite'),
                    created_at=parse_datetime(item.get('createdAt')) or datetime.now()
                )
                db.add(fvr_humain)
                fvr_h_count += 1
            db.commit()
            print(f"✅ {fvr_h_count} enregistrements FVR Humain importés")
        
        # Import FVR Animal
        if 'fvrAnimal' in data:
            print(f"\n📊 Import des données FVR Animal...")
            fvr_a_count = 0
            for item in data['fvrAnimal']:
                fvr_animal = FvrAnimal(
                    annee=item['annee'],
                    cas=item.get('cas', 0),
                    espece=item.get('espece'),
                    region=item.get('region'),
                    localisation=item.get('localisation'),
                    source=item.get('source'),
                    created_at=parse_datetime(item.get('createdAt')) or datetime.now()
                )
                db.add(fvr_animal)
                fvr_a_count += 1
            db.commit()
            print(f"✅ {fvr_a_count} enregistrements FVR Animal importés")
        
        # Import Grippe Aviaire
        if 'grippeAviaire' in data:
            print(f"\n📊 Import des données Grippe Aviaire...")
            ga_count = 0
            for item in data['grippeAviaire']:
                grippe = GrippeAviaire(
                    report_id=item['reportId'],
                    date_rapport=parse_date(item['dateRapport']),
                    region=item.get('region'),
                    espece=item.get('espece'),
                    maladie=item.get('maladie'),
                    cas_confirmes=item.get('casConfirmes', 0),
                    deces=item.get('deces', 0),
                    statut_epidemie=item.get('statutEpidemie'),
                    created_at=parse_datetime(item.get('createdAt')) or datetime.now()
                )
                db.add(grippe)
                ga_count += 1
            db.commit()
            print(f"✅ {ga_count} enregistrements Grippe Aviaire importés")
        
        # Import Pollution Air
        if 'pollutionAir' in data:
            print(f"\n📊 Import des données Pollution Air...")
            poll_count = 0
            for item in data['pollutionAir']:
                pollution = PollutionAir(
                    annee=item['annee'],
                    zone=item['zone'],
                    concentration_pm25=item.get('concentrationPm25'),
                    created_at=parse_datetime(item.get('createdAt')) or datetime.now()
                )
                db.add(pollution)
                poll_count += 1
            db.commit()
            print(f"✅ {poll_count} enregistrements Pollution Air importés")
        
        # Import Regions
        if 'regions' in data:
            print(f"\n📊 Import des données Régions...")
            region_count = 0
            for item in data['regions']:
                region = Region(
                    nom=item['nom'],
                    code=item['code'],
                    latitude=item.get('latitude'),
                    longitude=item.get('longitude'),
                    created_at=parse_datetime(item.get('createdAt')) or datetime.now()
                )
                db.add(region)
                region_count += 1
            db.commit()
            print(f"✅ {region_count} enregistrements Régions importés")
        
        print("\n" + "="*60)
        print("✅ IMPORT TERMINÉ AVEC SUCCÈS!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Erreur lors de l'import: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def verify_data(db: Session):
    """Vérifier les données importées"""
    print("\n" + "="*60)
    print("📊 VÉRIFICATION DES DONNÉES")
    print("="*60)
    
    malaria_count = db.query(Malaria).count()
    print(f"Paludisme: {malaria_count} enregistrements")
    
    tuberculose_count = db.query(Tuberculose).count()
    print(f"Tuberculose: {tuberculose_count} enregistrements")
    
    fvr_humain_count = db.query(FvrHumain).count()
    print(f"FVR Humain: {fvr_humain_count} enregistrements")
    
    fvr_animal_count = db.query(FvrAnimal).count()
    print(f"FVR Animal: {fvr_animal_count} enregistrements")
    
    grippe_count = db.query(GrippeAviaire).count()
    print(f"Grippe Aviaire: {grippe_count} enregistrements")
    
    pollution_count = db.query(PollutionAir).count()
    print(f"Pollution Air: {pollution_count} enregistrements")
    
    region_count = db.query(Region).count()
    print(f"Régions: {region_count} enregistrements")
    
    print("="*60)

if __name__ == "__main__":
    json_file = "/home/ubuntu/onehealth_dashboard_v3/database-export.json"
    
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    
    import_data_from_json(json_file)
    
    # Vérifier les données
    db = SessionLocal()
    verify_data(db)
    db.close()
