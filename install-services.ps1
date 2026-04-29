$workDir    = "C:\Users\Utilisateur\albou\2026\my_voice_lora"
$uvicorn    = "$workDir\.venv\Scripts\uvicorn.exe"
$caddy      = "$workDir\caddy_windows_amd64.exe"
$user       = $env:USERNAME
$trigger    = New-ScheduledTaskTrigger -AtStartup
$settings   = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)
$principal  = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Highest

# FastAPI
$actionApi = New-ScheduledTaskAction -Execute $uvicorn -Argument "api:app --host 127.0.0.1 --port 8000" -WorkingDirectory $workDir
Register-ScheduledTask -TaskName "VoiceLoraAPI" -Action $actionApi -Trigger $trigger -Settings $settings -Principal $principal -Force
Write-Host "VoiceLoraAPI enregistre" -ForegroundColor Green

# Caddy
$actionCaddy = New-ScheduledTaskAction -Execute $caddy -Argument "run --config $workDir\Caddyfile" -WorkingDirectory $workDir
Register-ScheduledTask -TaskName "VoiceLoraCaddy" -Action $actionCaddy -Trigger $trigger -Settings $settings -Principal $principal -Force
Write-Host "VoiceLoraCaddy enregistre" -ForegroundColor Green

# Demarrage immediat
Start-ScheduledTask -TaskName "VoiceLoraAPI"
Start-ScheduledTask -TaskName "VoiceLoraCaddy"
Write-Host "Services demarres !" -ForegroundColor Green
