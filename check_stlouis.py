from database import SessionLocal
from models import FvrHumain, FvrAnimal
from sqlalchemy import func

db = SessionLocal()

# FVR Humain pour Saint-Louis
fvr_h = db.query(func.sum(FvrHumain.cas_confirmes)).filter(
    FvrHumain.region == "Saint-Louis"
).scalar() or 0

# FVR Animal pour Saint-Louis
fvr_a = db.query(func.sum(FvrAnimal.cas)).filter(
    FvrAnimal.region == "Saint-Louis"
).scalar() or 0

print(f"Saint-Louis - FVR Humain: {fvr_h}")
print(f"Saint-Louis - FVR Animal: {fvr_a}")

# Voir tous les enregistrements
print("\nDétails FVR Humain Saint-Louis:")
for row in db.query(FvrHumain).filter(FvrHumain.region == "Saint-Louis").all():
    print(f"  - Date: {row.date_notification}, Cas: {row.cas_confirmes}")

print("\nDétails FVR Animal Saint-Louis:")
for row in db.query(FvrAnimal).filter(FvrAnimal.region == "Saint-Louis").all():
    print(f"  - Date: {row.date_detection}, Cas: {row.cas}")

db.close()
