@echo off
echo ========================================
echo Installation du Backend OneHealth
echo ========================================

REM Créer un environnement virtuel Python
echo.
echo Création de l'environnement virtuel Python...
python -m venv venv

REM Activer l'environnement virtuel
echo.
echo Activation de l'environnement virtuel...
call venv\Scripts\activate.bat

REM Installer les dépendances
echo.
echo Installation des dépendances Python...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ========================================
echo Installation terminée avec succès !
echo ========================================
echo.
echo Pour lancer le backend, exécutez : start_backend.bat
pause
