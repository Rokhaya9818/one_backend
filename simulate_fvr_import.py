import json
import os
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
from PIL import Image
from fvr_import_ocr import perform_ocr_on_image, extract_fvr_data_from_text, validate_and_import_fvr, FVRExtractedData, RegionData, DistrictData, ImportValidation
from models import FvrHumain
from sqlalchemy import func
import asyncio

# --- Données de test ---
# Chemin vers l'image du communiqué du 29 décembre
IMAGE_PATH_29_DEC = "/home/ubuntu/upload/pasted_file_5jtZ0M_image.png"

# Données simulées pour le 28 décembre (pour créer un point temporel)
DATA_28_DEC = {
    "date_reference": "2025-12-28",
    "total_cas_confirmes": 211,
    "total_deces": 21,
    "total_gueris": 162,
    "regions": [
        {"nom": "Saint-Louis", "total_cas": 211, "districts": []}
    ]
}
# --- Fonctions d'importation ---

async def import_simulated_data(data_dict: dict):
    db: Session = SessionLocal()
    
    print(f"\n--- 1. Importation des données simulées pour le {data_dict['date_reference']} ---")
    
    extracted_data = FVRExtractedData(
        date_communique=datetime.now().strftime("%Y-%m-%d"),
        date_reference=data_dict["date_reference"],
        total_cas_confirmes=data_dict["total_cas_confirmes"],
        total_deces=data_dict["total_deces"],
        total_gueris=data_dict["total_gueris"],
        regions=[RegionData(**r) for r in data_dict["regions"]],
        texte_brut="Données simulées",
        source="Simulation"
    )
    
    validation_data = ImportValidation(data=extracted_data, action="confirm")
    await validate_and_import_fvr(validation_data, db)
    
    db.close()

async def import_image_data(image_path: str):
    db: Session = SessionLocal()
    
    print(f"\n--- 2. Importation des données de l'image: {image_path} ---")
    
    # Lire l'image locale
    image = Image.open(image_path)
        
    # Effectuer l'OCR
    text = perform_ocr_on_image(image)
    
    if not text:
        print("Erreur: Aucune donnée OCR n'a été extraite.")
        return
        
    # Extraire les données
    extracted_dict = extract_fvr_data_from_text(text)
    
    # Construire l'objet FVRExtractedData
    extracted_data = FVRExtractedData(
        date_communique=datetime.now().strftime("%Y-%m-%d"),
        date_reference=datetime(2025, 12, 29).strftime("%Y-%m-%d"),
        total_cas_confirmes=extracted_dict["total_cas_confirmes"],
        total_deces=extracted_dict["total_deces"],
        total_gueris=extracted_dict["total_gueris"],
        regions=[RegionData(**r) for r in extracted_dict["regions"]],
        texte_brut=text,
        source=f"Local File: {image_path}"
    )
    
    validation_data = ImportValidation(data=extracted_data, action="confirm")
    await validate_and_import_fvr(validation_data, db)
    
    db.close()

# --- Fonction principale de simulation ---

async def simulate_import():
    
    # 0. RAZ de la base de données
    db: Session = SessionLocal()
    db.query(FvrHumain).delete()
    db.commit()
    db.close()
    
    # --- Importation du 28 décembre (Point 1) ---
    await import_simulated_data(DATA_28_DEC)
    
    # --- Importation du 29 décembre (Point 2) ---
    await import_image_data(IMAGE_PATH_29_DEC)
    
    # --- Vérification finale ---
    db: Session = SessionLocal()
    print("\n--- 3. Vérification des données importées ---")
    
    # Vérification des totaux
    total_cas = db.query(func.sum(FvrHumain.cas_confirmes)).scalar()
    total_deces = db.query(func.sum(FvrHumain.deces)).scalar()
    total_gueris = db.query(func.sum(FvrHumain.gueris)).scalar()
    
    print(f"Base de données - Total Cas Confirmés: {total_cas}")
    print(f"Base de données - Total Décès: {total_deces}")
    print(f"Base de données - Total Guéris: {total_gueris}")
    
    # Le total attendu est le total du dernier communiqué (558 cas, 31 décès, 527 guéris)
    if total_cas == 558 and total_deces == 31 and total_gueris == 527:
        print("✅ Succès: La logique d'arrondi et l'importation incrémentielle sont correctes.")
    else:
        print("❌ Échec: La logique d'arrondi ou l'importation incrémentielle a échoué.")
    
    db.close()

if __name__ == "__main__":
    # Nécessite d'être exécuté dans le répertoire backend pour les imports
    asyncio.run(simulate_import())
