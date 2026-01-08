# Fichier : backend/assistant.py
# Assistant IA enrichi avec données complètes et relations One Health

import os
import json
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
    if fvr_humain_total and fvr_humain_total > 0 and fvr_humain_deces and fvr_humain_deces > 0:
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
    malaria_indicators = db.query(
        Malaria.indicator_name,
        Malaria.numeric_value
    ).all()
    
    malaria_data = {}
    for indicator in malaria_indicators:
        if indicator[0] and indicator[1]:
            malaria_data[indicator[0]] = indicator[1]
    
    # ========== TUBERCULOSE ==========
    tuberculose_indicators = db.query(
        Tuberculose.indicator_name,
        Tuberculose.numeric_value
    ).all()
    
    tuberculose_data = {}
    for indicator in tuberculose_indicators:
        if indicator[0] and indicator[1]:
            tuberculose_data[indicator[0]] = indicator[1]
    
    # ========== ENVIRONNEMENT ==========
    pm25_avg = db.query(func.avg(PollutionAir.concentration_pm25.cast(Float))).scalar()
    pm25_max = db.query(func.max(PollutionAir.concentration_pm25.cast(Float))).scalar()
    
    pluie_avg = db.query(func.avg(Pluviometrie.pluie_moyenne.cast(Float))).scalar()
    
    # Construction du contexte global enrichi
    context_data = {
        "date_du_rapport": datetime.now().strftime("%d janvier %Y"),
        
        # ========== INFORMATIONS GÉNÉRALES ==========
        "informations_generales": {
            "fvr": "Fièvre de la Vallée du Rift - Maladie virale transmise par les moustiques (Aedes, Culex). Transmission possible entre animaux et humains. Symptômes: fièvre, hémorragies, complications oculaires.",
            "grippe_aviaire": "Maladie virale affectant les oiseaux et volailles. Transmission zoonotique possible aux humains. Surveillance stricte requise.",
            "malaria": "Maladie parasitaire transmise par les moustiques Anopheles femelles. Parasites: Plasmodium. Symptômes: fièvre, frissons, anémie. Fortement liée aux conditions climatiques (pluie, température, humidité).",
            "tuberculose": "Maladie infectieuse bactérienne (Mycobacterium tuberculosis). Transmission par voie aérienne. Affecte principalement les poumons. Liée aux conditions socio-économiques et à la malnutrition.",
            "pollution": "PM2.5 et autres polluants affectent les voies respiratoires et augmentent la vulnérabilité aux maladies infectieuses."
        },
        
        # ========== FVR HUMAIN ==========
        "fvr_humain": {
            "total_cas": int(fvr_humain_total) if fvr_humain_total else 0,
            "total_deces": int(fvr_humain_deces) if fvr_humain_deces else 0,
            "total_gueris": int(fvr_humain_gueris) if fvr_humain_gueris else 0,
            "taux_letalite": f"{taux_letalite_fvr}%",
            "description": "Nombre de cas confirmés de Fièvre de la Vallée du Rift chez l'homme au Sénégal",
            "regions": [
                {
                    "region": r[0],
                    "cas": int(r[1]) if r[1] else 0,
                    "deces": int(r[2]) if r[2] else 0
                } for r in fvr_humain_regions
            ]
        },
        
        # ========== FVR ANIMAL ==========
        "fvr_animal": {
            "total_cas": int(fvr_animal_total) if fvr_animal_total else 0,
            "description": "Nombre de cas de Fièvre de la Vallée du Rift détectés chez les animaux (ruminants, bovins, ovins, caprins)",
            "par_espece": [
                {
                    "espece": e[0] if e[0] else "Non spécifiée",
                    "cas": int(e[1]) if e[1] else 0
                } for e in fvr_animal_by_espece
            ],
            "importance": "La surveillance animale est cruciale car les animaux sont les réservoirs du virus et peuvent transmettre à l'homme"
        },
        
        # ========== GRIPPE AVIAIRE ==========
        "grippe_aviaire": {
            "total_incidents": int(grippe_aviaire_total) if grippe_aviaire_total else 0,
            "total_cas_confirmes": int(grippe_aviaire_cas) if grippe_aviaire_cas else 0,
            "total_deces": int(grippe_aviaire_deces) if grippe_aviaire_deces else 0,
            "description": "Incidents de grippe aviaire détectés au Sénégal",
            "risque": "Zoonose avec potentiel pandémique. Surveillance étroite des volailles et oiseaux migrateurs requise."
        },
        
        # ========== PALUDISME ==========
        "paludisme": {
            "description": "Maladie parasitaire transmise par les moustiques Anopheles. Indicateurs clés de surveillance.",
            "indicateurs": malaria_data if malaria_data else {
                "Cas suspects": "À déterminer",
                "Cas confirmés": "À déterminer",
                "Décès": "À déterminer"
            },
            "facteurs_risque": [
                "Saison des pluies (augmente les gîtes larvaires)",
                "Température élevée (accélère le développement du parasite)",
                "Humidité relative (favorise la survie des moustiques)",
                "Accès limité aux moustiquaires imprégnées",
                "Traitement insuffisant"
            ]
        },
        
        # ========== TUBERCULOSE ==========
        "tuberculose": {
            "description": "Maladie infectieuse bactérienne. Indicateurs de surveillance et contrôle.",
            "indicateurs": tuberculose_data if tuberculose_data else {
                "Cas notifiés": "À déterminer",
                "Taux de guérison": "À déterminer",
                "Abandon de traitement": "À déterminer"
            },
            "facteurs_risque": [
                "Malnutrition",
                "Immunodépression (VIH/SIDA)",
                "Surpeuplement",
                "Mauvaise ventilation",
                "Conditions socio-économiques précaires"
            ]
        },
        
        # ========== ENVIRONNEMENT ==========
        "environnement": {
            "pm25_moyenne": round(float(pm25_avg), 2) if pm25_avg else 0.0,
            "pm25_max": round(float(pm25_max), 2) if pm25_max else 0.0,
            "pluie_moyenne": round(float(pluie_avg), 2) if pluie_avg else 0.0,
            "description": "Indicateurs environnementaux affectant la transmission des maladies",
            "impacts": {
                "pollution_pm25": "Augmente la vulnérabilité respiratoire et facilite les infections",
                "pluie": "Crée des gîtes pour les moustiques (Aedes, Anopheles, Culex), augmente le risque de paludisme et FVR",
                "temperature": "Accélère le développement des parasites et des vecteurs",
                "humidite": "Favorise la survie et la reproduction des moustiques"
            }
        },
        
        # ========== RELATIONS ONE HEALTH ==========
        "relations_one_health": {
            "definition": "L'approche One Health reconnaît l'interconnexion entre la santé humaine, animale et environnementale.",
            "exemples": [
                {
                    "scenario": "Saison des pluies + Température élevée + Humidité",
                    "consequence": "Augmentation des gîtes larvaires → Prolifération des moustiques Anopheles → Épidémie de paludisme",
                    "maladies_affectees": ["Paludisme", "FVR", "Dengue"]
                },
                {
                    "scenario": "FVR chez les animaux (ruminants)",
                    "consequence": "Transmission zoonotique aux humains par contact avec animaux infectés ou vecteurs",
                    "maladies_affectees": ["FVR Humain"]
                },
                {
                    "scenario": "Pollution de l'air (PM2.5 élevée)",
                    "consequence": "Affaiblissement du système respiratoire → Vulnérabilité accrue aux infections",
                    "maladies_affectees": ["Tuberculose", "Grippe", "Infections respiratoires"]
                },
                {
                    "scenario": "Grippe aviaire chez les oiseaux migrateurs",
                    "consequence": "Transmission à la volaille domestique → Risque de transmission zoonotique aux humains",
                    "maladies_affectees": ["Grippe Aviaire"]
                },
                {
                    "scenario": "Malnutrition + Conditions socio-économiques précaires",
                    "consequence": "Immunodépression → Vulnérabilité à la tuberculose et autres infections opportunistes",
                    "maladies_affectees": ["Tuberculose", "Infections diverses"]
                }
            ],
            "recommandations": [
                "Surveillance intégrée des maladies humaines, animales et environnementales",
                "Gestion des vecteurs (moustiques) pour contrôler paludisme et FVR",
                "Amélioration de la qualité de l'air pour réduire les maladies respiratoires",
                "Renforcement de la surveillance des zoonoses (FVR, Grippe Aviaire)",
                "Amélioration des conditions socio-économiques pour prévenir la tuberculose",
                "Coordination entre secteurs: santé, agriculture, environnement"
            ]
        }
    }
    
    return json.dumps(context_data, indent=2, ensure_ascii=False)

# ============================================================================
# LOGIQUE DE L'ASSISTANT IA
# ============================================================================

def ask_ai_assistant(question: str, db: Session) -> str:
    """
    Envoie la question de l'utilisateur et le contexte complet à l'API OpenRouter.
    """
    
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY non configurée.")

    # 1. Récupérer le contexte complet
    context_data = get_dashboard_context(db)
    
    # 2. Définir le rôle de l'IA avec instructions détaillées
    system_prompt = (
        "Tu es 'OneHealth Assistant', un assistant IA expert en santé publique, épidémiologie et approche One Health "
        "pour le Ministère de la Santé du Sénégal.\n\n"
        
        "DOMAINES D'EXPERTISE:\n"
        "1. Fièvre de la Vallée du Rift (FVR) - Humain et Animal\n"
        "2. Grippe Aviaire - Zoonose et surveillance\n"
        "3. Paludisme - Transmission par moustiques, facteurs climatiques\n"
        "4. Tuberculose - Maladie bactérienne, facteurs socio-économiques\n"
        "5. Environnement - Pollution, climat, vecteurs\n"
        "6. One Health - Relations entre santé humaine, animale et environnementale\n\n"
        
        "INFORMATIONS IMPORTANTES À RETENIR:\n"
        "- FVR = Fièvre de la Vallée du Rift (maladie virale transmise par moustiques)\n"
        "- FVR Humain = cas confirmés chez l'homme\n"
        "- FVR Animal = cas chez les animaux (réservoirs du virus)\n"
        "- Grippe Aviaire = 7 incidents actuellement\n"
        "- Paludisme = Maladie parasitaire, fortement liée aux conditions climatiques\n"
        "- Tuberculose = Maladie bactérienne, liée aux conditions socio-économiques\n"
        "- PM2.5 = Polluant affectant la santé respiratoire\n\n"
        
        "RÈGLES DE RÉPONSE:\n"
        "1. Base toutes tes réponses sur les données du contexte fourni\n"
        "2. Fournis des informations détaillées et précises sur chaque maladie\n"
        "3. Explique les relations One Health quand pertinent\n"
        "4. Donne les chiffres exacts et les régions affectées\n"
        "5. Explique les facteurs de risque et les relations entre maladies et environnement\n"
        "6. Si une information n'est pas disponible, le mentionner clairement\n"
        "7. Réponds en français de manière structurée et professionnelle\n"
        "8. Fournis des recommandations basées sur l'approche One Health"
    )
    
    # 3. Construire le message pour l'IA
    user_message = (
        f"CONTEXTE COMPLET DU DASHBOARD ONE HEALTH (JSON) :\n{context_data}\n\n"
        f"QUESTION DE L'UTILISATEUR :\n{question}"
    )
    
    try:
        # 4. Appel à l'API OpenRouter
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,  # Légèrement plus élevé pour plus de détails
        )
        
        # 5. Retourner la réponse de l'IA
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Erreur lors de l'appel à OpenRouter: {e}")
        return (
            "Désolé, une erreur est survenue lors de la communication avec l'intelligence artificielle. "
            "Veuillez vérifier la configuration de la clé OpenRouter et la disponibilité du service. "
            f"Détail de l'erreur: {e}"
        )
