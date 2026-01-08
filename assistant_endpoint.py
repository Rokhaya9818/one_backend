# Fichier : backend/assistant_endpoint.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from assistant import ask_ai_assistant

router = APIRouter()

# Schéma de la requête utilisateur
class ChatRequest(BaseModel):
    message: str

# Schéma de la réponse de l'IA
class ChatResponse(BaseModel):
    answer: str

@router.post("/api/assistant/chat", response_model=ChatResponse)
def chat_with_assistant(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Endpoint pour interagir avec l'Assistant IA.
    Prend une question en entrée et retourne la réponse de l'IA basée sur le contexte du dashboard.
    """
    try:
        # Appel à la fonction principale de l'assistant
        ai_answer = ask_ai_assistant(request.message, db)
        
        return ChatResponse(answer=ai_answer)
        
    except HTTPException as e:
        # Relancer les exceptions HTTP (pour l'erreur de clé API)
        raise e
    except Exception as e:
        # Gérer les autres erreurs internes et renvoyer le détail
        print(f"Erreur interne dans l'endpoint /chat: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur lors de la communication avec l'IA: {e}")
