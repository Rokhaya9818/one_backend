@echo off
echo ========================================
echo Démarrage du Backend OneHealth
echo ========================================

REM Activer l'environnement virtuel
call venv\Scripts\activate.bat

REM Lancer le serveur FastAPI
echo.
echo Lancement du serveur FastAPI sur http://localhost:8000
echo.
uvicorn main:app --reload --host 0.0.0.0 --port 8000
