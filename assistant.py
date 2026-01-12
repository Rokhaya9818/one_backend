# Fichier : backend/assistant.py corrigé
# Assistant IA enrichi avec données complètes et relations One Health

import os
import json
import requests
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

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://onehealth-senegal.netlify.app",
        "X-Title": "OneHealth Dashboard Sénégal",
    }
)

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
        
        taux_letalite_fvr = 0
        if fvr_humain_total and fvr_humain_total > 0 and fvr_humain_deces:
            taux_letalite_fvr = round((fvr_humain_deces / fvr_humain_total) * 100, 2)
        
        # ========== FVR ANIMAL ==========
        fvr_animal_total = db.query(func.sum(FvrAnimal.cas)).scalar()
        
        # ========== GRIPPE AVIAIRE ==========
        # Correction : S'assurer de sommer les cas confirmés
        grippe_aviaire_cas = db.query(func.sum(GrippeAviaire.cas_confirmes)).scalar()
        grippe_aviaire_deces = db.query(func.sum(GrippeAviaire.deces)).scalar()
        
        # ========== PALUDISME (MALARIA) ==========
        malaria_indicators = db.query(Malaria.indicator_name, Malaria.numeric_value).all()
        malaria_data = {i[0]: i[1] for i in malaria_indicators if i[0] and i[1] is not None}
        
        # ========== TUBERCULOSE ==========
        tuberculose_indicators = db.query(Tuberculose.indicator_name, Tuberculose.numeric_value).all()
        tuberculose_data = {i[0]: i[1] for i in tuberculose_indicators if i[0] and i[1] is not None}
        
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
            "grippe_aviaire": {
                "total_cas": int(grippe_aviaire_cas or 0),
                "total_deces": int(grippe_aviaire_deces or 0)
            },
            "paludisme": malaria_data,
            "tuberculose": tuberculose_data,
            "environnement": {
                "pm25_moyenne": round(float(pm25_avg or 0), 2),
                "pluie_moyenne": round(float(pluie_avg or 0), 2),
                "impact_sante": "Une concentration élevée de PM2.5 aggrave les maladies respiratoires comme la tuberculose. Les fortes pluies favorisent la prolifération des moustiques vecteurs du paludisme et de la FVR."
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
        raise HTTPException(status_code=500, detail="Configuration API manquante sur le serveur.")

    context_data = get_dashboard_context(db)
    
    system_prompt = (
        "Tu es 'OneHealth Assistant', un expert en santé publique au Sénégal. "
        "Tu dois impérativement utiliser les données fournies dans le contexte JSON pour répondre. "
        "Si une donnée est présente dans le JSON (comme le paludisme, la tuberculose ou la grippe aviaire), utilise-la. "
        "Si on te demande l'impact de la pollution, explique le lien entre PM2.5 et maladies respiratoires. "
        "Si on te demande l'impact de l'environnement sur le palu, explique le lien avec la pluviométrie. "
        "Sois précis, professionnel et structure tes réponses avec des chiffres concrets."
    )
    
    user_message = f"CONTEXTE:\n{context_data}\n\nQUESTION: {question}"
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.2, # Réduit pour plus de précision factuelle
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        # Tentative de secours simplifiée
        try:
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": MODEL_NAME, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]}
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                return res.json()['choices'][0]['message']['content']
            return f"Erreur API: {res.status_code}"
        except:
            return f"Erreur critique: {str(e)}"
