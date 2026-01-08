from database import SessionLocal
from models import FvrHumain, FvrAnimal
from sqlalchemy import func

db = SessionLocal()

print("=== Analyse détaillée Saint-Louis ===\n")

# Méthode 1: Somme directe
fvr_h_direct = db.query(func.sum(FvrHumain.cas_confirmes)).filter(
    FvrHumain.region == "Saint-Louis"
).scalar() or 0
print(f"Méthode 1 (somme directe): {fvr_h_direct} cas humains")

# Méthode 2: Compter les enregistrements
count_records = db.query(FvrHumain).filter(FvrHumain.region == "Saint-Louis").count()
print(f"Nombre d'enregistrements: {count_records}")

# Méthode 3: Lister tous les cas
print("\nDétail de tous les enregistrements:")
for row in db.query(FvrHumain).filter(FvrHumain.region == "Saint-Louis").all():
    print(f"  ID: {row.id}, Cas confirmés: {row.cas_confirmes}")

# Vérifier s'il y a des duplications
print("\n=== Vérification des duplications ===")
all_regions = db.query(FvrHumain.region, func.count(FvrHumain.id)).group_by(FvrHumain.region).all()
for region, count in all_regions:
    if region == "Saint-Louis":
        print(f"{region}: {count} enregistrements")

db.close()
