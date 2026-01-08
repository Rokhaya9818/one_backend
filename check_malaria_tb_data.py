import os
from sqlalchemy import create_engine, func, distinct
from sqlalchemy.orm import sessionmaker
from models import Malaria, Tuberculose, MalariaRegional, Base
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
        print("--- Vérification des données MalariaRegional ---")
        
        # 1. Compter les enregistrements dans MalariaRegional
        malaria_count = db.query(MalariaRegional).count()
        print(f"Total d'enregistrements dans MalariaRegional: {malaria_count}")
        
        # 2. Exécuter la logique de l'endpoint /malaria-by-indicator
        malaria_results = db.query(
            MalariaRegional.region,
            func.sum(MalariaRegional.cas_confirmes).label('count')
        ).filter(
            MalariaRegional.region.isnot(None)
        ).group_by(
            MalariaRegional.region
        ).all()
        
        print("\nRésultats de l'agrégation Malaria par Région:")
        if malaria_results:
            for r in malaria_results:
                print(f"  Région: {r.region}, Cas Confirmés: {r.count}")
        else:
            print("  Aucun résultat trouvé pour MalariaRegional.")

        print("\n--- Vérification des données Tuberculose ---")
        
        # 3. Compter les enregistrements dans Tuberculose
        tuberculose_count = db.query(Tuberculose).count()
        print(f"Total d'enregistrements dans Tuberculose: {tuberculose_count}")
        
        # 4. Exécuter la logique de l'endpoint /tuberculose-by-indicator
        tuberculose_results = db.query(
            Tuberculose.indicator_code,
            func.count(Tuberculose.id).label('count')
        ).group_by(
            Tuberculose.indicator_code
        ).all()
        
        print("\nRésultats de l'agrégation Tuberculose par Code Indicateur:")
        if tuberculose_results:
            for r in tuberculose_results:
                print(f"  Code: {r.indicator_code}, Nombre d'indicateurs: {r.count}")
        else:
            print("  Aucun résultat trouvé pour Tuberculose.")
            
    except Exception as e:
        print(f"Une erreur s'est produite lors de la vérification de la base de données: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Assurez-vous que les modèles sont importables (nécessite models.py dans le même répertoire)
    # Le script sera exécuté depuis le répertoire backend.
    os.chdir("/home/ubuntu/onehealth_dashboard_FINAL_COMPLET/onehealth_ULTRA_COMPLET/backend")
    check_data()
