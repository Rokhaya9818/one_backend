from database import SessionLocal
from models import FvrHumain
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func

# Données du communiqué du 29 décembre 2025
# Données du communiqué du 29 décembre 2025
COMMUNIQUE_DATE_29 = date(2025, 12, 29)

# Données simulées pour le 28 décembre 2025
COMMUNIQUE_DATE_28 = date(2025, 12, 28)
TOTAL_CAS_28 = 211
TOTAL_DECES_28 = 21
TOTAL_GUERIS_28 = 162
REGIONAL_DATA_28 = [
    {"region": "Saint-Louis", "cas": 211, "deces": 0, "gueris": 0},
]

# Totaux nationaux du 29 décembre
TOTAL_CAS_29 = 555 # Total national du communiqué (basé sur la somme des régions)
TOTAL_DECES_29 = 31
TOTAL_GUERIS_29 = 527

# Répartition régionale du 29 décembre
REGIONAL_DATA_29 = [
    {"region": "Saint-Louis", "cas": 372, "deces": 0, "gueris": 0},
    {"region": "Fatick", "cas": 39, "deces": 0, "gueris": 0},
    {"region": "Louga", "cas": 22, "deces": 0, "gueris": 0},
    {"region": "Matam", "cas": 45, "deces": 0, "gueris": 0},
    {"region": "Kaolack", "cas": 36, "deces": 0, "gueris": 0},
    {"region": "Dakar", "cas": 18, "deces": 0, "gueris": 0},
    {"region": "Kédougou", "cas": 2, "deces": 0, "gueris": 0},
    {"region": "Tambacounda", "cas": 10, "deces": 0, "gueris": 0},
    {"region": "Thiès", "cas": 5, "deces": 0, "gueris": 0},
    {"region": "Kaffrine", "cas": 2, "deces": 0, "gueris": 0},
    {"region": "Kolda", "cas": 4, "deces": 0, "gueris": 0},
]

def inject_data_for_date(db: Session, date_bilan: date, total_cas: int, total_deces: int, total_gueris: int, regional_data: list):
    
    total_cas_injected = 0
    
    for data in regional_data:
        # Calcul de la proportion
        proportion = data["cas"] / total_cas
        
        # Répartition des décès et guéris (arrondi simple)
        deces_region = round(total_deces * proportion)
        gueris_region = round(total_gueris * proportion)
        
        # Création de l'enregistrement FvrHumain (au niveau régional)
        fvr_entry = FvrHumain(
            date_bilan=date_bilan,
            region=data["region"],
            cas_confirmes=data["cas"],
            deces=deces_region,
            gueris=gueris_region,
            district=None # Représente le total régional
        )
        db.add(fvr_entry)
        total_cas_injected += data["cas"]
        
    # 3. Vérification et ajustement des totaux
    injected_deces = db.query(func.sum(FvrHumain.deces)).filter(FvrHumain.date_bilan == date_bilan).scalar() or 0
    injected_gueris = db.query(func.sum(FvrHumain.gueris)).filter(FvrHumain.date_bilan == date_bilan).scalar() or 0
    
    # Ajustement sur la première région (Saint-Louis)
    deces_diff = total_deces - injected_deces
    gueris_diff = total_gueris - injected_gueris
    
    if deces_diff != 0 or gueris_diff != 0:
        print(f"Ajustement nécessaire pour {date_bilan}: Décès ({deces_diff}), Guéris ({gueris_diff})")
        
        # Récupérer l'enregistrement de Saint-Louis pour cette date
        st_louis = db.query(FvrHumain).filter(FvrHumain.region == "Saint-Louis", FvrHumain.date_bilan == date_bilan).first()
        
        if st_louis:
            st_louis.deces += deces_diff
            st_louis.gueris += gueris_diff
            print(f"Ajustement appliqué à Saint-Louis pour {date_bilan}.")
    
    db.commit()

def inject_fvr_data():
    db: Session = SessionLocal()
    
    try:
        # 1. Suppression des anciennes données FVR Humain
        db.query(FvrHumain).delete()
        db.commit()
        print("Anciennes données FVR Humain supprimées.")
        
        # --- Injection du 28 décembre ---
        inject_data_for_date(db, COMMUNIQUE_DATE_28, TOTAL_CAS_28, TOTAL_DECES_28, TOTAL_GUERIS_28, REGIONAL_DATA_28)
        
        # --- Injection du 29 décembre ---
        inject_data_for_date(db, COMMUNIQUE_DATE_29, TOTAL_CAS_29, TOTAL_DECES_29, TOTAL_GUERIS_29, REGIONAL_DATA_29)
        
        # 4. Vérification finale
        final_cas = db.query(func.sum(FvrHumain.cas_confirmes)).scalar() or 0
        final_deces = db.query(func.sum(FvrHumain.deces)).scalar() or 0
        final_gueris = db.query(func.sum(FvrHumain.gueris)).scalar() or 0
        
        print(f"\nInjection terminée. Totaux finaux:")
        print(f"Cas Confirmés: {final_cas} (Attendu: {TOTAL_CAS_29})")
        print(f"Décès: {final_deces} (Attendu: {TOTAL_DECES_29})")
        print(f"Guéris: {final_gueris} (Attendu: {TOTAL_GUERIS_29})")
        
        if final_cas == TOTAL_CAS_29 and final_deces == TOTAL_DECES_29 and final_gueris == TOTAL_GUERIS_29:
            print("✅ Succès: Les données FVR Humain ont été injectées correctement.")
        else:
            print(f"❌ Échec: Les totaux injectés ne correspondent pas aux totaux du communiqué. Cas: {final_cas} (Attendu: {TOTAL_CAS_29}), Décès: {final_deces} (Attendu: {TOTAL_DECES_29}), Guéris: {final_gueris} (Attendu: {TOTAL_GUERIS_29})")
            
    except Exception as e:
        db.rollback()
        print(f"Erreur lors de l'injection des données: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inject_fvr_data()
