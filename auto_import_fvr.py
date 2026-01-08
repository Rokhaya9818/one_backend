"""
Script d'import automatique des données FVR depuis la page Facebook du Ministère de la Santé
Version 2 - Avec Selenium pour contourner les protections Facebook
Exécution quotidienne à 18h
"""

import os
import re
import time
import random
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, List, Optional
from PIL import Image
import pytesseract
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fvr_auto_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
FACEBOOK_PAGE_URL = "https://www.facebook.com/MinSanteSN"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://onehealth_user:onehealth2025@localhost:5432/onehealth")
DOWNLOAD_DIR = Path("./fvr_downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Créer la connexion à la base de données
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class FVRDataExtractor:
    """Extracteur de données FVR depuis les communiqués Facebook avec Selenium"""
    
    def __init__(self):
        self.driver = None
    
    def init_selenium(self):
        """Initialise le navigateur Selenium avec Chrome headless"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Navigateur Selenium initialisé")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de Selenium: {e}")
            raise
    
    def get_latest_post_images(self) -> List[str]:
        """
        Récupère l'URL de l'image du premier post Facebook contenant FVR avec Selenium.
        S'arrête dès qu'un post contenant 'FVR' ou 'Fièvre de la Vallée du Rift' est trouvé.
        """
        try:
            if not self.driver:
                self.init_selenium()
            
            # Accéder à la page Facebook
            logger.info(f"Accès à {FACEBOOK_PAGE_URL}...")
            self.driver.get(FACEBOOK_PAGE_URL)
            
            # Attendre le chargement de la page
            time.sleep(random.uniform(3, 5))
            
            # Chercher les images dans les posts avec scroll
            images = []
            fvr_found = False
            scroll_attempts = 0
            max_scrolls = 15  # Limiter à 15 scrolls pour éviter un scroll infini
            
            try:
                while not fvr_found and scroll_attempts < max_scrolls:
                    # Trouver toutes les images visibles
                    img_elements = self.driver.find_elements(By.TAG_NAME, "img")
                    
                    for img in img_elements:
                        src = img.get_attribute("src")
                        if src and ('scontent' in src or 'fbcdn' in src) and src not in images:
                            # Filtrer les petites images (icônes, avatars)
                            try:
                                width = img.get_attribute("width")
                                height = img.get_attribute("height")
                                if width and height:
                                    w = int(width) if width.isdigit() else 0
                                    h = int(height) if height.isdigit() else 0
                                    if w > 200 and h > 200:  # Ignorer les petites images
                                        images.append(src)
                            except:
                                if src not in images:
                                    images.append(src)
                
                    # Vérifier si on a trouvé un post mentionnant FVR
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if "FVR" in page_text or "Fièvre de la Vallée du Rift" in page_text:
                        logger.info(f"Post FVR détecté après {scroll_attempts + 1} scroll(s)")
                        fvr_found = True
                        break
                    
                    # Scroller vers le bas pour charger plus de posts
                    self.driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(random.uniform(2, 3))
                    scroll_attempts += 1
                    logger.info(f"Scroll {scroll_attempts}/{max_scrolls}...")
                
                if fvr_found:
                    logger.info(f"Trouvé {len(images)} image(s) dans le post FVR (après {scroll_attempts} scrolls)")
                
            except Exception as e:
                logger.error(f"Erreur lors de la recherche des images: {e}")
            
            # Retourner la première image trouvée
            return images[:1]  # Limiter à 1 image pour le premier post contenant FVR
    
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des posts Facebook: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def download_image(self, url: str, filename: str) -> Optional[Path]:
        """Télécharge une image depuis une URL"""
        try:
            import requests
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            filepath = DOWNLOAD_DIR / filename
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Image téléchargée: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement de l'image: {e}")
            return None
    
    def extract_text_from_image(self, image_path: Path) -> str:
        """Extrait le texte d'une image avec OCR (Tesseract)"""
        try:
            # Ouvrir l'image avec PIL
            image = Image.open(image_path)
            
            # --- Prétraitement de l'image pour améliorer l'OCR ---
            # 1. Convertir en niveaux de gris
            image = image.convert('L')
            
            # 2. Appliquer une binarisation (seuillage)
            # Le seuil 128 est un bon point de départ pour le noir et blanc
            threshold = 128
            image = image.point(lambda x: 0 if x < threshold else 255, '1')
            # --- Fin du Prétraitement ---
            
            # Configurer Tesseract pour le français
            custom_config = r'--oem 3 --psm 3 -l fra' # PSM 3 pour une page entière de texte, plus robuste que PSM 6
            text = pytesseract.image_to_string(image, config=custom_config)
            
            logger.info(f"Texte extrait de {image_path.name}: {len(text)} caractères")
            return text
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction OCR: {e}")
            return ""
    
    def parse_fvr_data(self, text: str) -> Optional[Dict]:
        """
        Parse les données FVR depuis le texte extrait
        Format attendu: "Saint-Louis : 344 cas", "31 décès", "446 guéris"
        """
        try:
            # Vérifier que c'est bien un communiqué FVR
            if "Fièvre de la Vallée du Rift" not in text and "FVR" not in text:
                logger.info("Ce n'est pas un communiqué FVR")
                return None
            
            # Extraire la date
            date_match = re.search(r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})', text, re.IGNORECASE)
            if date_match:
                day, month_fr, year = date_match.groups()
                months = {
                    'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
                    'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
                    'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
                }
                date = datetime(int(year), months[month_fr.lower()], int(day))
            else:
                date = datetime.now()
            
            # Extraire les totaux (cas confirmés, décès, guéris)
            total_cases = 0
            total_deaths = 0
            total_recovered = 0
            
            cases_match = re.search(r'(\d+)\s+cas\s+confirmés', text, re.IGNORECASE)
            if cases_match:
                total_cases = int(cases_match.group(1))
            
            deaths_match = re.search(r'(\d+)\s+décès', text, re.IGNORECASE)
            if deaths_match:
                total_deaths = int(deaths_match.group(1))
            
            recovered_match = re.search(r'(\d+)\s+guéris', text, re.IGNORECASE)
            if recovered_match:
                total_recovered = int(recovered_match.group(1))
            
            # Extraire les données par région
            regions_data = []
            
            # Pattern pour "Saint-Louis : 344 cas"
            region_pattern = r'(\d+)\.\s*([\w\s-]+)\s*:\s*(\d+)\s+cas' # Capture le numéro, le nom de la région (plus souple), et le nombre de cas
            for match in re.finditer(region_pattern, text):
                region_name = match.group(2).strip()
                cases = int(match.group(3))
                
                
                # Normaliser le nom de la région
                region_name = self.normalize_region_name(region_name)
                
                if region_name:
                    regions_data.append({
                        'region': region_name,
                        'cases': cases
                    })
            
            if not regions_data:
                logger.warning("Aucune donnée régionale trouvée")
                return None
            
            result = {
                'date': date,
                'total_cases': total_cases,
                'total_deaths': total_deaths,
                'total_recovered': total_recovered,
                'regions': regions_data
            }
            
            logger.info(f"Données FVR parsées: {total_cases} cas, {len(regions_data)} régions")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing des données FVR: {e}")
            return None
    
    def normalize_region_name(self, name: str) -> Optional[str]:
        """Normalise le nom d'une région"""
        # Mapping des variations de noms
        region_mapping = {
            'saint-louis': 'Saint-Louis',
            'saint louis': 'Saint-Louis',
            'fatick': 'Fatick',
            'louga': 'Louga',
            'matam': 'Matam',
            'kaolack': 'Kaolack',
            'dakar': 'Dakar',
            'kédougou': 'Kédougou',
            'kedougou': 'Kédougou',
            'tambacounda': 'Tambacounda',
            'thiès': 'Thiès',
            'thies': 'Thiès',
            'kaffrine': 'Kaffrine',
            'kolda': 'Kolda',
            'région kolda': 'Kolda',
            'sédhiou': 'Sédhiou',
            'sedhiou': 'Sédhiou',
            'ziguinchor': 'Ziguinchor',
            'diourbel': 'Diourbel'
        }
        
        name_lower = name.lower().strip()
        return region_mapping.get(name_lower)
    
    def cleanup_old_images(self):
        """Nettoie les anciennes images téléchargées"""
        try:
            for file in DOWNLOAD_DIR.glob("*.jpg"):
                # Supprimer les fichiers de plus de 7 jours
                if time.time() - file.stat().st_mtime > 7 * 24 * 3600:
                    file.unlink()
                    logger.info(f"Image supprimée: {file.name}")
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")


class FVRDatabaseUpdater:
    """Gestionnaire de mise à jour de la base de données"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def check_if_already_imported(self, date: datetime) -> bool:
        """Vérifie si les données de cette date ont déjà été importées"""
        try:
            query = text("""
                SELECT COUNT(*) FROM fvr_humain 
                WHERE DATE(date_bilan) = :date
            """)
            result = self.db.execute(query, {'date': date.date()}).scalar()
            return result > 0
        except Exception as e:
            logger.error(f"Erreur lors de la vérification: {e}")
            return False
    
    def insert_fvr_data(self, data: Dict) -> bool:
        """Insère les nouvelles données FVR dans la base"""
        try:
            # IMPORTANT: Supprimer les anciennes données avant d'insérer les nouvelles
            # Cela évite la duplication (les communiqués contiennent le total cumulé, pas les nouveaux cas)
            delete_query = text("""
                DELETE FROM fvr_humain 
                WHERE district IS NULL
            """)
            self.db.execute(delete_query)
            logger.info("Anciennes données FVR supprimées avant insertion")
            
            # Insérer les nouvelles données par région
            for region_data in data['regions']:
                query = text("""
                    INSERT INTO fvr_humain (
                        region, date_bilan, cas_confirmes, deces, gueris
                    ) VALUES (
                        :region, :date, :cases, :deaths, :recovered
                    )
""")
                
                self.db.execute(query, {
                    'region': region_data['region'],
                    'date': data['date'],
                    'cases': region_data['cases'],
                    'deaths': data['total_deaths'] if region_data['region'] == 'Saint-Louis' else 0,  # Les totaux sont stockés avec la première région pour le bilan global
                    'recovered': data['total_recovered'] if region_data['region'] == 'Saint-Louis' else 0  # Les totaux sont stockés avec la première région pour le bilan global
                })
            
            self.db.commit()
            logger.info(f"✅ Données FVR importées avec succès: {len(data['regions'])} régions")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erreur lors de l'insertion des données: {e}")
            return False
    
    def close(self):
        """Ferme la connexion à la base de données"""
        self.db.close()


def main():
    """Fonction principale d'import automatique"""
    logger.info("=" * 60)
    logger.info("DÉMARRAGE DE L'IMPORT AUTOMATIQUE FVR")
    logger.info("=" * 60)
    
    try:
        # Initialiser les composants
        extractor = FVRDataExtractor()
        updater = FVRDatabaseUpdater()
        
        # Récupérer les images des posts récents
        logger.info("Récupération des posts Facebook avec Selenium...")
        image_urls = extractor.get_latest_post_images()
        
        if not image_urls:
            logger.warning("Aucune image trouvée sur la page Facebook")
            return
        
        # Traiter l'image trouvée
        for i, url in enumerate(image_urls):
            logger.info(f"\n--- Traitement de l'image {i+1}/{len(image_urls)} ---")
            
            # Télécharger l'image
            filename = f"communique_{datetime.now().strftime('%Y%m%d')}_{i+1}.jpg"
            image_path = extractor.download_image(url, filename)
            
            if not image_path:
                continue
            
            # Extraire le texte avec OCR
            text = extractor.extract_text_from_image(image_path)
            
            if not text:
                continue
            
            # Parser les données FVR
            fvr_data = extractor.parse_fvr_data(text)
            
            if fvr_data:
                # Insérer dans la base de données
                success = updater.insert_fvr_data(fvr_data)
                
                if success:
                    logger.info("✅ IMPORT RÉUSSI!")
                    break  # Arrêter après le premier import réussi
            else:
                logger.info("Ce post ne contient pas de données FVR exploitables")
        
        # Nettoyer les anciennes images
        extractor.cleanup_old_images()
        
        # Fermer les connexions
        updater.close()
        
        logger.info("\n" + "=" * 60)
        logger.info("FIN DE L'IMPORT AUTOMATIQUE FVR")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)


if __name__ == "__main__":
    main()