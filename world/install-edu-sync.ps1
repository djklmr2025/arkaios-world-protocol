# Registra (o actualiza) la tarea programada que trae las solicitudes de plantillas de
# Educación Libre al tablero de ARKAIOS World cada 30 minutos, solo con la sesión iniciada.
#   powershell -ExecutionPolicy Bypass -File world\install-edu-sync.ps1
#   Para quitarla: Unregister-ScheduledTask -TaskName ARKAIOS_World_EduSync -Confirm:$false
$repo = Split-Path -Parent $PSScriptRoot
$action = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument "//B `"$repo\world\edu-sync-hidden.vbs`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 30)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'ARKAIOS_World_EduSync' -Force `
    -Description 'Trae solicitudes de plantillas de Educacion Libre al tablero de ARKAIOS World (cada 30 min).' `
    -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Select-Object TaskName, State
Write-Host "Log: $repo\.local-world\edu-sync.log"
