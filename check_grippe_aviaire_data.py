import os
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import GrippeAviaire
from dotenv import load_dotenv

# Charger les variables d'environnement (pour la DATABASE_URL)
load_dotenv()

# Remplacer par les credentials Dokploy
DATABASE_URL = "postgresql+psycopg2://postgres:tofnm2nut4bsdsel@dokploy.eyone.net:6432/preprod_admin_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_data():
    db = SessionLocal()
    try:
        print("--- Vérification des données GrippeAviaire ---")
        
        # 1. Compter les enregistrements dans GrippeAviaire
        grippe_count = db.query(GrippeAviaire).count()
        print(f"Total d'enregistrements dans GrippeAviaire: {grippe_count}")
        
        # 2. Compter les cas confirmés (pour vérifier l'ancienne logique)
        cas_confirmes_total = db.query(func.sum(GrippeAviaire.cas_confirmes)).scalar() or 0
        print(f"Total des cas confirmés (somme de la colonne cas_confirmes): {cas_confirmes_total}")
        
        # 3. Compter les incidents non résolus (pour vérifier la logique par défaut du KPI)
        non_resolu_count = db.query(GrippeAviaire).filter(GrippeAviaire.statut_epidemie != 'Resolved').count()
        print(f"Total des incidents non résolus: {non_resolu_count}")
        
    except Exception as e:
        print(f"Une erreur s'est produite lors de la vérification de la base de données: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Le script est exécuté depuis le répertoire backend.
    check_data()
