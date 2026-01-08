"""
Endpoint pour l'import FVR avec OCR (upload d'image ou lien Facebook)
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import FvrHumain
from pydantic import BaseModel
from typing import List, Optional
import re
from datetime import datetime
import pytesseract
from PIL import Image
import requests
from io import BytesIO
import os

router = APIRouter()

class DistrictData(BaseModel):
    nom: str
    cas: int

class RegionData(BaseModel):
    nom: str
    total_cas: int
    districts: List[DistrictData]

class FVRExtractedData(BaseModel):
    date_communique: str
    date_reference: str
    total_cas_confirmes: int
    total_deces: int
    total_gueris: int
    regions: List[RegionData]
    texte_brut: str
    source: str

class FacebookLinkRequest(BaseModel):
    url: str

class ImportValidation(BaseModel):
    data: FVRExtractedData
    action: str  # "confirm" ou "cancel"

def extract_fvr_data_from_text(text: str) -> dict:
    """
    Extrait les données FVR d'un texte de communiqué
    """
    result = {
        "total_cas_confirmes": 0,
        "total_deces": 0,
        "total_gueris": 0,
        "regions": []
    }
    
    # Extraire les statistiques nationales
    # Extraire les statistiques nationales
    cas_pattern = r'(\d+)\s*cas\s+confirmés'
    deces_pattern = r'(\d+)\s*décès'
    gueris_pattern = r'(\d+)\s*guéris'

    cas_match = re.search(cas_pattern, text, re.IGNORECASE)
    deces_match = re.search(deces_pattern, text, re.IGNORECASE)
    gueris_match = re.search(gueris_pattern, text, re.IGNORECASE)

    if cas_match:
        result["total_cas_confirmes"] = int(cas_match.group(1))
    if deces_match:
        result["total_deces"] = int(deces_match.group(1))
    if gueris_match:
        result["total_gueris"] = int(gueris_match.group(1))
    
    # Extraire les régions et leurs cas
    # Format: "1. Saint-Louis : 365 cas" ou "Région de Saint-Louis : 365 cas"
    region_pattern = r'(?:\d+\.\s+|Région\s+de\s+)([A-Za-zéèêëàâäôöùûüçÉÈÊËÀÂÄÔÖÙÛÜÇ\s-]+?)\s*:\s*(\d+)\s*cas'
    region_matches = re.finditer(region_pattern, text, re.IGNORECASE)
    
    for region_match in region_matches:
        region_name = region_match.group(1).strip()
        region_total = int(region_match.group(2))
        
        # Ne pas extraire les districts
        districts = []
        
        result["regions"].append({
            "nom": region_name,
            "total_cas": region_total,
            "districts": districts
        })
    
    return result

def extract_date_from_text(text: str) -> Optional[str]:
    """
    Extrait la date du communiqué
    """
    months = {
        'janvier': '01', 'février': '02', 'fevrier': '02', 'mars': '03',
        'avril': '04', 'mai': '05', 'juin': '06', 'juillet': '07',
        'août': '08', 'aout': '08', 'septembre': '09', 'octobre': '10',
        'novembre': '11', 'décembre': '12', 'decembre': '12'
    }
    
    date_pattern = r'(\d{1,2})\s+(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\s+(\d{4})'
    date_match = re.search(date_pattern, text, re.IGNORECASE)
    
    if date_match:
        day = date_match.group(1).zfill(2)
        month = months.get(date_match.group(2).lower(), '01')
        year = date_match.group(3)
        return f"{year}-{month}-{day}"
    
    return None

def perform_ocr_on_image(image: Image.Image) -> str:
    """
    Effectue l'OCR sur une image PIL
    """
    try:
        # Configuration de Tesseract pour le français
        custom_config = r'--oem 3 --psm 6 -l fra'
        text = pytesseract.image_to_string(image, config=custom_config)
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur OCR: {str(e)}")

def download_facebook_image(url: str) -> Image.Image:
    """
    Télécharge une image depuis Facebook
    """
    try:
        # Ajouter les headers pour éviter le blocage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        image = Image.open(BytesIO(response.content))
        return image
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de télécharger l'image: {str(e)}"
        )

@router.post("/api/fvr/import/upload", response_model=FVRExtractedData)
async def import_fvr_from_upload(file: UploadFile = File(...)):
    """
    Import FVR depuis une image uploadée
    """
    try:
        # Lire l'image uploadée
        contents = await file.read()
        image = Image.open(BytesIO(contents))
        
        # Effectuer l'OCR
        text = perform_ocr_on_image(image)
        
        if not text or len(text) < 50:
            raise HTTPException(
                status_code=400,
                detail="Aucun texte détecté dans l'image. Assurez-vous que l'image est claire et lisible."
            )
        
        # Extraire les données
        extracted_data = extract_fvr_data_from_text(text)
        
        # Extraire les dates
        date_communique = extract_date_from_text(text)
        if not date_communique:
            date_communique = datetime.now().strftime("%Y-%m-%d")
        
        date_ref_match = re.search(r'à\s+la\s+date\s+du\s+(\d{1,2})\s+(\w+)\s+(\d{4})', text, re.IGNORECASE)
        if date_ref_match:
            months = {
                'janvier': '01', 'février': '02', 'fevrier': '02', 'mars': '03',
                'avril': '04', 'mai': '05', 'juin': '06', 'juillet': '07',
                'août': '08', 'aout': '08', 'septembre': '09', 'octobre': '10',
                'novembre': '11', 'décembre': '12', 'decembre': '12'
            }
            day = date_ref_match.group(1).zfill(2)
            month = months.get(date_ref_match.group(2).lower(), '01')
            year = date_ref_match.group(3)
            date_reference = f"{year}-{month}-{day}"
        else:
            date_reference = date_communique
        
        return FVRExtractedData(
            date_communique=date_communique,
            date_reference=date_reference,
            total_cas_confirmes=extracted_data["total_cas_confirmes"],
            total_deces=extracted_data["total_deces"],
            total_gueris=extracted_data["total_gueris"],
            regions=extracted_data["regions"],
            texte_brut=text,
            source=f"Upload: {file.filename}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du traitement de l'image: {str(e)}"
        )

@router.post("/api/fvr/import/facebook-link", response_model=FVRExtractedData)
async def import_fvr_from_facebook_link(request: FacebookLinkRequest):
    """
    Import FVR depuis un lien Facebook
    """
    try:
        # Extraire l'URL de l'image depuis le lien Facebook
        # Pour un lien comme https://www.facebook.com/photo?fbid=xxx
        # On peut essayer de récupérer l'image directement
        
        # Méthode 1: Si c'est un lien direct vers une image
        if 'fbcdn.net' in request.url or request.url.endswith(('.jpg', '.jpeg', '.png')):
            image = download_facebook_image(request.url)
        else:
            # Méthode 2: Utiliser Selenium pour récupérer l'image depuis la page
            raise HTTPException(
                status_code=400,
                detail="Pour les liens Facebook, veuillez utiliser le lien direct de l'image (clic droit > Copier l'adresse de l'image) ou uploadez l'image directement."
            )
        
        # Effectuer l'OCR
        text = perform_ocr_on_image(image)
        
        if not text or len(text) < 50:
            raise HTTPException(
                status_code=400,
                detail="Aucun texte détecté dans l'image. Assurez-vous que l'image est claire et lisible."
            )
        
        # Extraire les données
        extracted_data = extract_fvr_data_from_text(text)
        
        # Extraire les dates
        date_communique = extract_date_from_text(text)
        if not date_communique:
            date_communique = datetime.now().strftime("%Y-%m-%d")
        
        date_ref_match = re.search(r'à\s+la\s+date\s+du\s+(\d{1,2})\s+(\w+)\s+(\d{4})', text, re.IGNORECASE)
        if date_ref_match:
            months = {
                'janvier': '01', 'février': '02', 'fevrier': '02', 'mars': '03',
                'avril': '04', 'mai': '05', 'juin': '06', 'juillet': '07',
                'août': '08', 'aout': '08', 'septembre': '09', 'octobre': '10',
                'novembre': '11', 'décembre': '12', 'decembre': '12'
            }
            day = date_ref_match.group(1).zfill(2)
            month = months.get(date_ref_match.group(2).lower(), '01')
            year = date_ref_match.group(3)
            date_reference = f"{year}-{month}-{day}"
        else:
            date_reference = date_communique
        
        return FVRExtractedData(
            date_communique=date_communique,
            date_reference=date_reference,
            total_cas_confirmes=extracted_data["total_cas_confirmes"],
            total_deces=extracted_data["total_deces"],
            total_gueris=extracted_data["total_gueris"],
            regions=extracted_data["regions"],
            texte_brut=text,
            source=f"Facebook: {request.url}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du traitement du lien: {str(e)}"
        )

@router.post("/api/fvr/import/validate")
async def validate_and_import_fvr(
    validation: ImportValidation,
    db: Session = Depends(get_db)
):
    """
    Valide et importe les données FVR extraites
    """
    
    if validation.action != "confirm":
        return {"status": "cancelled", "message": "Import annulé par l'utilisateur"}
    
    data = validation.data
    imported_count = 0
    
    try:
        date_bilan = datetime.strptime(data.date_reference, "%Y-%m-%d").date()
        
        # IMPORTANT: Supprimer toutes les anciennes données avant d'insérer les nouvelles
        # Les communiqués contiennent le total cumulé depuis le début, pas les nouveaux cas
        db.query(FvrHumain).filter(FvrHumain.district.is_(None)).delete()
        
        # Initialiser les accumulateurs pour la compensation d'arrondi
        total_deces_attribues = 0
        total_gueris_attribues = 0
        
        # Importer les données par région (total cumulé)
        for idx, region in enumerate(data.regions):
            # Nettoyer le nom de la région
            region_name = region.nom.replace("Région ", "").replace("Region ", "")
            
            # Calculer les décès et guéris proportionnels pour la région
            region_deces = 0
            region_gueris = 0
            
            # Utiliser la répartition proportionnelle pour la majorité des régions
            if data.total_cas_confirmes > 0:
                region_deces = round((region.total_cas / data.total_cas_confirmes) * data.total_deces)
                region_gueris = round((region.total_cas / data.total_cas_confirmes) * data.total_gueris)
            
            # Mettre à jour les accumulateurs pour la prochaine itération
            total_deces_attribues += region_deces
            total_gueris_attribues += region_gueris
            
            # Logique de compensation pour la dernière région
            if idx == len(data.regions) - 1:
                # Ajuster la dernière région pour que le total corresponde
                region_deces = data.total_deces - (total_deces_attribues - region_deces)
                region_gueris = data.total_gueris - (total_gueris_attribues - region_gueris)
            
            # Calculer le taux de létalité pour cette région
            taux_letalite = "0"
            if region.total_cas > 0:
                taux_letalite = f"{(region_deces / region.total_cas * 100):.1f}"
            
            # Créer un enregistrement pour la région avec le TOTAL CUMULÉ
            fvr_region = FvrHumain(
                date_bilan=date_bilan,
                region=region_name,
                district=None,
                cas_confirmes=region.total_cas,  # Total cumulé, pas nouveaux cas
                deces=region_deces,
                gueris=region_gueris,
                taux_letalite=taux_letalite
            )
            db.add(fvr_region)
            imported_count += 1
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"{len(data.regions)} régions importées avec succès.",
            "total_cas": data.total_cas_confirmes,
            "total_deces": data.total_deces,
            "total_gueris": data.total_gueris,
            "regions_count": len(data.regions),
            "records_count": imported_count
        }
        
    except HTTPException:
        # Re-lever les HTTPException sans les modifier (pour les doublons, etc.)
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'import: {str(e)}"
        )
