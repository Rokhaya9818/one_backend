@echo off
REM Script pour exécuter l'import automatique FVR

REM Activer l'environnement virtuel
call "%~dp0venv\Scripts\activate.bat"

REM Lancer le script d'import
python "%~dp0auto_import_fvr.py"
