# Registra (o actualiza) la tarea programada que trae las solicitudes de plantillas de
# Educación Libre al tablero de ARKAIOS World cada 10 minutos, solo con la sesión iniciada, y
# de paso arranca ARKAIOS World si no responde en :4300 (vigilante).
#   powershell -ExecutionPolicy Bypass -File C:\ARKAIOS\arkaios-world-protocol\world\install-edu-sync.ps1
#   Para quitarla: Unregister-ScheduledTask -TaskName ARKAIOS_World_EduSync -Confirm:$false
$repo = Split-Path -Parent $PSScriptRoot
$action = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument "//B `"$repo\world\edu-sync-hidden.vbs`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 10)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'ARKAIOS_World_EduSync' -Force `
    -Description 'Trae solicitudes de plantillas de Educacion Libre al tablero de ARKAIOS World (cada 10 min) y mantiene ARKAIOS World levantado.' `
    -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Select-Object TaskName, State
Write-Host "Log: $repo\.local-world\edu-sync.log"
