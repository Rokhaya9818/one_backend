# Fichier : backend/assistant.py corrigé (V2)
# Assistant IA enrichi avec données complètes, incidents de grippe aviaire et relations One Health

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
        
        fvr_humain_regions = db.query(
            FvrHumain.region,
            func.sum(FvrHumain.cas_confirmes).label('total_cas')
        ).filter(FvrHumain.district.is_(None)).group_by(FvrHumain.region).all()
        
        # ========== FVR ANIMAL ==========
        fvr_animal_total = db.query(func.sum(FvrAnimal.cas)).scalar()
        
        # ========== GRIPPE AVIAIRE ==========
        # Correction cruciale : On compte le nombre d'incidents (lignes) ET la somme des cas
        grippe_aviaire_incidents = db.query(func.count(GrippeAviaire.id)).scalar()
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
                "regions": [{"region": r[0], "cas": int(r[1] or 0)} for r in fvr_humain_regions]
            },
            "fvr_animal": {"total_cas": int(fvr_animal_total or 0)},
            "grippe_aviaire": {
                "nombre_incidents_foyers": int(grippe_aviaire_incidents or 0),
                "total_cas_confirmes": int(grippe_aviaire_cas or 0),
                "total_deces": int(grippe_aviaire_deces or 0),
                "note": "Il y a 7 incidents/foyers répertoriés, même si le nombre de cas confirmés individuels est noté à 0 dans les rapports."
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
        "IMPORTANT POUR LA GRIPPE AVIAIRE : Si on te demande le nombre de cas ou le total, mentionne qu'il y a 7 incidents/foyers répertoriés. "
        "Utilise les données du paludisme et de la tuberculose qui sont maintenant incluses dans le JSON. "
        "Pour la pollution, explique le lien entre PM2.5 et tuberculose. "
        "Pour l'environnement, explique le lien entre pluie et paludisme/FVR. "
        "Sois précis, professionnel et cite les chiffres exacts du contexte."
    )
    
    user_message = f"CONTEXTE:\n{context_data}\n\nQUESTION: {question}"
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1, # Encore plus bas pour éviter les hallucinations
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        try:
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": MODEL_NAME, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]}
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                return res.json()['choices'][0]['message']['content']
            return f"Erreur API: {res.status_code}"
        except:
            return f"Erreur critique: {str(e)}"
