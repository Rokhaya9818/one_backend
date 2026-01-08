from database import SessionLocal
from models import FvrHumain, FvrAnimal
from sqlalchemy import func

db = SessionLocal()

# Requête exacte utilisée dans l'endpoint
correlations_query = db.query(
    FvrHumain.region,
    func.sum(FvrHumain.cas_confirmes).label('fvr_h'),
    func.sum(FvrAnimal.cas).label('fvr_a')
).join(
    FvrAnimal, FvrHumain.region == FvrAnimal.region
).group_by(FvrHumain.region)

print("Résultats de la requête JOIN:")
for row in correlations_query:
    if row.region == "Saint-Louis":
        print(f"Région: {row.region}")
        print(f"FVR Humain (fvr_h): {row.fvr_h}")
        print(f"FVR Animal (fvr_a): {row.fvr_a}")

db.close()
