# Script PowerShell pour configurer le Planificateur de Tâches Windows
# Exécution automatique de l'import FVR tous les jours à 18h00

$TaskName = "OneHealth_Import_FVR_Quotidien"
$ScriptPath = "$PSScriptRoot\run_fvr_import.bat"
$Description = "Import automatique des données FVR depuis Facebook vers la base PostgreSQL distante"

# Vérifier si la tâche existe déjà
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($ExistingTask) {
    Write-Host "La tâche '$TaskName' existe déjà. Suppression..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Créer le déclencheur (tous les jours à 18h00)
$Trigger = New-ScheduledTaskTrigger -Daily -At 18:00

# Créer l'action (exécuter le script batch)
$Action = New-ScheduledTaskAction -Execute $ScriptPath -WorkingDirectory $PSScriptRoot

# Créer les paramètres de la tâche
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Enregistrer la tâche
Register-ScheduledTask -TaskName $TaskName -Trigger $Trigger -Action $Action -Settings $Settings -Description $Description

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Planification configurée avec succès !" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Tâche : $TaskName" -ForegroundColor Cyan
Write-Host "Heure d'exécution : Tous les jours à 18h00" -ForegroundColor Cyan
Write-Host "Script : $ScriptPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pour tester l'import manuellement, lancez :" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
Write-Host ""
Write-Host "Pour voir les logs, consultez : fvr_auto_import.log" -ForegroundColor Yellow
Write-Host ""
