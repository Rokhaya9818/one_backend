from sqlalchemy import func
from database import SessionLocal
from models import FvrHumain

def check_fvr_humain_totals():
    db = SessionLocal()
    try:
        # Calculer les totaux
        total_cas = db.query(func.sum(FvrHumain.cas_confirmes)).scalar() or 0
        total_deces = db.query(func.sum(FvrHumain.deces)).scalar() or 0
        total_gueris = db.query(func.sum(FvrHumain.gueris)).scalar() or 0
        
        # Calculer le taux de létalité
        taux_letalite = (total_deces / total_cas * 100) if total_cas > 0 else 0.0
        
        print("--- Totaux FVR Humain dans la base de données ---")
        print(f"Total Cas Confirmés: {total_cas}")
        print(f"Total Décès: {total_deces}")
        print(f"Total Guéris: {total_gueris}")
        print(f"Taux de Létalité Calculé: {round(taux_letalite, 1)}%")
        
        # Afficher les enregistrements pour Saint-Louis
        saint_louis_records = db.query(FvrHumain).filter(FvrHumain.region == "Saint-Louis").all()
        print("\n--- Enregistrements FVR Humain pour Saint-Louis ---")
        for record in saint_louis_records:
            print(f"ID: {record.id}, Date: {record.date_bilan}, Cas: {record.cas_confirmes}, Décès: {record.deces}, Guéris: {record.gueris}")

    finally:
        db.close()

if __name__ == "__main__":
    check_fvr_humain_totals()
