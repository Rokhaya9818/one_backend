from database import engine, Base
from models import (
    User, Malaria, Tuberculose, FvrHumain, FvrAnimal,
    GrippeAviaire, Pluviometrie, PollutionAir, AnimalMortalite, Region
)

def init_database():
    """Créer toutes les tables dans la base de données"""
    print("Création des tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables créées avec succès!")

if __name__ == "__main__":
    init_database()
