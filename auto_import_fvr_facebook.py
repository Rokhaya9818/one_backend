"""
Endpoint pour l'import automatique des données FVR depuis Facebook avec Selenium
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import FvrHumain
from pydantic import BaseModel
from typing import List, Optional
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
from dotenv import load_dotenv

load_dotenv()

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
    source_url: str

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
    stats_pattern = r'(\d+)\s*cas\s+confirmés.*?(\d+)\s*décès.*?(\d+)\s*guéris'
    stats_match = re.search(stats_pattern, text, re.IGNORECASE | re.DOTALL)
    if stats_match:
        result["total_cas_confirmes"] = int(stats_match.group(1))
        result["total_deces"] = int(stats_match.group(2))
        result["total_gueris"] = int(stats_match.group(3))
    
    # Extraire les régions et leurs cas
    region_pattern = r'Région\s+de\s+([^:]+?)\s*:\s*(\d+)\s*cas'
    region_matches = re.finditer(region_pattern, text, re.IGNORECASE)
    
    for region_match in region_matches:
        region_name = region_match.group(1).strip()
        region_total = int(region_match.group(2))
        
        # Trouver les districts de cette région
        region_start = region_match.end()
        next_region = re.search(r'Région\s+de\s+', text[region_start:], re.IGNORECASE)
        
        if next_region:
            region_text = text[region_start:region_start + next_region.start()]
        else:
            next_section = re.search(r'\d+[-\.]?\s*(Mpox|Contact|Pour toute)', text[region_start:], re.IGNORECASE)
            if next_section:
                region_text = text[region_start:region_start + next_section.start()]
            else:
                region_text = text[region_start:region_start + 500]
        
        # Extraire les districts
        district_pattern = r'District\s+([^:]+?)\s*:\s*(\d+)\s*cas'
        district_matches = re.finditer(district_pattern, region_text, re.IGNORECASE)
        
        districts = []
        for district_match in district_matches:
            district_name = district_match.group(1).strip()
            district_cas = int(district_match.group(2))
            districts.append({
                "nom": district_name,
                "cas": district_cas
            })
        
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

def login_to_facebook(driver, email: str, password: str) -> bool:
    """
    Se connecter à Facebook avec Selenium
    """
    try:
        # Aller sur Facebook
        driver.get("https://www.facebook.com")
        time.sleep(3)
        
        # Trouver et remplir le formulaire de connexion
        email_input = driver.find_element(By.ID, "email")
        password_input = driver.find_element(By.ID, "pass")
        
        email_input.send_keys(email)
        password_input.send_keys(password)
        
        # Cliquer sur le bouton de connexion
        login_button = driver.find_element(By.NAME, "login")
        login_button.click()
        
        # Attendre que la connexion soit complète
        time.sleep(5)
        
        # Vérifier si la connexion a réussi
        if "login" in driver.current_url.lower():
            return False
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de la connexion: {str(e)}")
        return False

@router.get("/api/fvr/auto-import/scrape", response_model=FVRExtractedData)
async def scrape_facebook_fvr():
    """
    Scrape la page Facebook du Ministère de la Santé avec Selenium et login
    """
    
    # Récupérer les identifiants depuis les variables d'environnement
    facebook_email = os.getenv("FACEBOOK_EMAIL")
    facebook_password = os.getenv("FACEBOOK_PASSWORD")
    
    if not facebook_email or not facebook_password:
        raise HTTPException(
            status_code=500,
            detail="Identifiants Facebook non configurés dans le fichier .env"
        )
    
    # URL de la page Facebook du Ministère de la Santé du Sénégal
    facebook_url = "https://www.facebook.com/MinSanteSN"
    
    # Configuration de Selenium
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = None
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        # Se connecter à Facebook
        if not login_to_facebook(driver, facebook_email, facebook_password):
            raise HTTPException(
                status_code=401,
                detail="Échec de la connexion à Facebook. Vérifiez les identifiants."
            )
        
        # Aller sur la page du Ministère
        driver.get(facebook_url)
        time.sleep(5)
        
        # Faire défiler pour charger les posts
        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(3)
        
        # Chercher les posts contenant "FVR" ou "Fièvre de la Vallée du Rift"
        posts = driver.find_elements(By.CSS_SELECTOR, "[data-ad-preview='message'], [role='article']")
        
        fvr_post_text = None
        
        # Parcourir les posts pour trouver un communiqué FVR
        for post in posts[:15]:  # Vérifier les 15 derniers posts
            try:
                post_text = post.text
                if re.search(r'(FVR|Fièvre de la Vallée du Rift|Fiévre de la Vallée|Point de situation)', post_text, re.IGNORECASE):
                    # Vérifier si c'est bien un communiqué avec des données (contient "cas confirmés")
                    if re.search(r'cas\s+confirmés', post_text, re.IGNORECASE):
                        fvr_post_text = post_text
                        break
            except:
                continue
        
        if not fvr_post_text:
            raise HTTPException(
                status_code=404,
                detail="Aucun communiqué FVR trouvé sur la page Facebook"
            )
        
        # Extraire les données du texte
        extracted_data = extract_fvr_data_from_text(fvr_post_text)
        
        # Extraire la date du communiqué
        date_communique = extract_date_from_text(fvr_post_text)
        if not date_communique:
            date_communique = datetime.now().strftime("%Y-%m-%d")
        
        # Extraire la date de référence
        date_ref_match = re.search(r'à\s+la\s+date\s+du\s+(\d{1,2})\s+(\w+)\s+(\d{4})', fvr_post_text, re.IGNORECASE)
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
            texte_brut=fvr_post_text,
            source_url=facebook_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du scraping: {str(e)}"
        )
    
    finally:
        if driver:
            driver.quit()

@router.post("/api/fvr/auto-import/validate")
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
        # Importer les données par région
        for region in data.regions:
            # Créer ou mettre à jour l'enregistrement pour la région
            fvr_record = FvrHumain(
                region=region.nom,
                cas_confirmes=region.total_cas,
                deces=0,  # Les décès sont au niveau national
                date_import=datetime.now(),
                source="Facebook - Ministère de la Santé",
                date_reference=datetime.strptime(data.date_reference, "%Y-%m-%d").date()
            )
            
            db.add(fvr_record)
            imported_count += 1
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"{imported_count} régions importées avec succès",
            "total_cas": data.total_cas_confirmes,
            "total_deces": data.total_deces,
            "total_gueris": data.total_gueris
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'import: {str(e)}"
        )
