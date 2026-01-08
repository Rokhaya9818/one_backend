"""
Endpoint API pour l'import automatique FVR
À ajouter dans main.py
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import subprocess
import os

router = APIRouter(prefix="/api/fvr-import", tags=["FVR Import"])


class ImportStatus(BaseModel):
    status: str
    message: str
    timestamp: datetime


class ImportHistory(BaseModel):
    date: datetime
    total_cases: int
    regions_count: int
    status: str


@router.post("/launch", response_model=ImportStatus)
async def launch_fvr_import(background_tasks: BackgroundTasks):
    """Lance l'import FVR en arrière-plan"""
    try:
        # Lancer le script d'import en arrière-plan
        script_path = os.path.join(os.path.dirname(__file__), "auto_import_fvr.py")
        
        # Exécuter le script
        result = subprocess.run(
            ["python3", script_path],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            return ImportStatus(
                status="success",
                message="Import FVR lancé avec succès",
                timestamp=datetime.now()
            )
        else:
            return ImportStatus(
                status="error",
                message=f"Erreur lors de l'import: {result.stderr}",
                timestamp=datetime.now()
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[ImportHistory])
async def get_import_history():
    """Récupère l'historique des imports FVR"""
    try:
        from database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        
        # Récupérer les imports groupés par date
        query = text("""
            SELECT 
                DATE(date_bilan) as import_date,
                COUNT(*) as regions_count,
                SUM(cas_confirmes) as total_cases
            FROM fvr_humain
            GROUP BY DATE(date_bilan)
            ORDER BY DATE(date_bilan) DESC
            LIMIT 30
        """)
        
        results = db.execute(query).fetchall()
        db.close()
        
        history = []
        for row in results:
            history.append(ImportHistory(
                date=row[0],
                total_cases=row[2] or 0,
                regions_count=row[1] or 0,
                status="completed"
            ))
        
        return history
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_import_logs():
    """Récupère les derniers logs d'import"""
    try:
        log_file = os.path.join(os.path.dirname(__file__), "fvr_auto_import.log")
        
        if not os.path.exists(log_file):
            return {"logs": "Aucun log disponible"}
        
        # Lire les 50 dernières lignes
        with open(log_file, 'r') as f:
            lines = f.readlines()
            last_lines = lines[-50:] if len(lines) > 50 else lines
        
        return {"logs": "".join(last_lines)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
