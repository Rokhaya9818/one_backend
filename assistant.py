# Fichier : backend/assistant.py corrigé
# Assistant IA enrichi avec données complètes et relations One Health

import os
import json
import requests # Utilisation de requests pour un contrôle total des en-têtes si nécessaire
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import func, text, Float
from database import get_db
from models import FvrHumain, FvrAnimal, PollutionAir, Malaria, Tuberculose, GrippeAviaire, Pluviometrie
from datetime import datetime
from fastapi import Depends, HTTPException

# Charger les variables d'environnement
load_dotenv()

# ============================================================================
# CONFIGURATION OPENROUTER
# ============================================================================

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# Initialisation du client avec les en-têtes recommandés par OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://onehealth-senegal.netlify.app", # Remplacez par votre URL réelle
        "X-Title": "OneHealth Dashboard Sénégal",
    }
)

# Utilisation d'un modèle plus standard si mistral échoue
MODEL_NAME = "mistralai/mistral-7b-instruct" 

# ============================================================================
# EXTRACTION DU CONTEXTE COMPLET DE LA BASE DE DONNÉES
# ============================================================================

def get_dashboard_context(db: Session) -> str:
    """
    Extrait les données complètes du dashboard incluant toutes les maladies,
    indicateurs environnementaux et relations One Health.
    """
    try:
        # ========== FVR HUMAIN ==========
        fvr_humain_total = db.query(func.sum(FvrHumain.cas_confirmes)).filter(FvrHumain.district.is_(None)).scalar()
        fvr_humain_deces = db.query(func.sum(FvrHumain.deces)).filter(FvrHumain.district.is_(None)).scalar()
        fvr_humain_gueris = db.query(func.sum(FvrHumain.gueris)).filter(FvrHumain.district.is_(None)).scalar()
        
        fvr_humain_regions = db.query(
            FvrHumain.region,
            func.sum(FvrHumain.cas_confirmes).label('total_cas'),
            func.sum(FvrHumain.deces).label('total_deces')
        ).filter(FvrHumain.district.is_(None)).group_by(FvrHumain.region).order_by(func.sum(FvrHumain.cas_confirmes).desc()).all()
        
        # Calcul du taux de létalité FVR
        taux_letalite_fvr = 0
        if fvr_humain_total and fvr_humain_total > 0 and fvr_humain_deces:
            taux_letalite_fvr = round((fvr_humain_deces / fvr_humain_total) * 100, 2)
        
        # ========== FVR ANIMAL ==========
        fvr_animal_total = db.query(func.sum(FvrAnimal.cas)).scalar()
        fvr_animal_by_espece = db.query(
            FvrAnimal.espece,
            func.sum(FvrAnimal.cas).label('total_cas')
        ).group_by(FvrAnimal.espece).order_by(func.sum(FvrAnimal.cas).desc()).all()
        
        # ========== GRIPPE AVIAIRE ==========
        grippe_aviaire_total = db.query(func.count(GrippeAviaire.id)).scalar()
        grippe_aviaire_cas = db.query(func.sum(GrippeAviaire.cas_confirmes)).scalar()
        grippe_aviaire_deces = db.query(func.sum(GrippeAviaire.deces)).scalar()
        
        # ========== PALUDISME ==========
        malaria_indicators = db.query(Malaria.indicator_name, Malaria.numeric_value).all()
        malaria_data = {i[0]: i[1] for i in malaria_indicators if i[0] and i[1]}
        
        # ========== TUBERCULOSE ==========
        tuberculose_indicators = db.query(Tuberculose.indicator_name, Tuberculose.numeric_value).all()
        tuberculose_data = {i[0]: i[1] for i in tuberculose_indicators if i[0] and i[1]}
        
        # ========== ENVIRONNEMENT ==========
        pm25_avg = db.query(func.avg(PollutionAir.concentration_pm25.cast(Float))).scalar()
        pluie_avg = db.query(func.avg(Pluviometrie.pluie_moyenne.cast(Float))).scalar()

        context_data = {
            "date_du_rapport": datetime.now().strftime("%d %B %Y"),
            "fvr_humain": {
                "total_cas": int(fvr_humain_total or 0),
                "total_deces": int(fvr_humain_deces or 0),
                "taux_letalite": f"{taux_letalite_fvr}%",
                "regions": [{"region": r[0], "cas": int(r[1] or 0)} for r in fvr_humain_regions]
            },
            "fvr_animal": {"total_cas": int(fvr_animal_total or 0)},
            "grippe_aviaire": {"total_cas": int(grippe_aviaire_cas or 0)},
            "environnement": {
                "pm25_moyenne": round(float(pm25_avg or 0), 2),
                "pluie_moyenne": round(float(pluie_avg or 0), 2)
            }
        }
        return json.dumps(context_data, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur lors de l'extraction du contexte: {e}")
        return "Données du dashboard indisponibles actuellement."

# ============================================================================
# LOGIQUE DE L'ASSISTANT IA
# ============================================================================

def ask_ai_assistant(question: str, db: Session) -> str:
    """
    Envoie la question de l'utilisateur et le contexte complet à l'API OpenRouter.
    """
    
    if not OPENROUTER_API_KEY:
        print("ERREUR: OPENROUTER_API_KEY est vide ou non trouvée dans l'environnement.")
        raise HTTPException(status_code=500, detail="Configuration API manquante sur le serveur.")

    # 1. Récupérer le contexte
    context_data = get_dashboard_context(db)
    
    # 2. Définir le rôle de l'IA
    system_prompt = (
        "Tu es 'OneHealth Assistant', un expert en santé publique au Sénégal. "
        "Réponds en utilisant les données fournies dans le contexte JSON. "
        "Sois précis, professionnel et structure tes réponses."
    )
    
    # 3. Construire le message
    user_message = f"CONTEXTE:\n{context_data}\n\nQUESTION: {question}"
    
    try:
        # 4. Appel à l'API OpenRouter via le client OpenAI
        # On vérifie si la clé commence bien par sk-or-
        if not OPENROUTER_API_KEY.startswith("sk-or-"):
            print(f"ATTENTION: La clé API ne semble pas être au format OpenRouter (sk-or-...): {OPENROUTER_API_KEY[:10]}...")

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Erreur lors de l'appel à OpenRouter: {e}")
        
        # Tentative de secours avec requests direct si le client OpenAI échoue
        try:
            print("Tentative de secours via requests direct...")
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://onehealth-senegal.netlify.app",
                "X-Title": "OneHealth Dashboard Sénégal",
            }
            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            }
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                return res.json()['choices'][0]['message']['content']
            else:
                error_detail = res.text
                print(f"Échec du secours: {res.status_code} - {error_detail}")
                return f"Erreur d'authentification OpenRouter (401). Veuillez vérifier que la clé est bien configurée dans Render sous le nom OPENROUTER_API_KEY et qu'elle est active."
        except Exception as e2:
            return f"Erreur critique de communication avec l'IA: {str(e)}"
