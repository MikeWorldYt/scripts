<#
Optimizador conservador y reversible para Windows 10.
Ejecutar en PowerShell como administrador, con la cuenta del usuario que usa el PC.
#>
[CmdletBinding()]
param(
    [ValidateSet('Menu', 'Aplicar', 'Restaurar')]
    [string] $Accion = 'Menu'
)

$ErrorActionPreference = 'Stop'
$BackupDirectory = Join-Path $PSScriptRoot 'respaldos'
$LogPath = Join-Path $PSScriptRoot ("cambios-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))

function Write-ChangeLog {
    param([string]$Target, [string]$Before, [string]$After, [string]$Result = 'Aplicado')
    $line = "{0}`t{1}`t{2}`t{3}`t{4}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Result, $Target, $Before, $After
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
}

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Assert-Windows10 {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        throw 'Este script solo funciona en Windows.'
    }
    $version = Get-CimInstance Win32_OperatingSystem
    if ([int]$version.BuildNumber -lt 10240 -or [int]$version.BuildNumber -ge 22000) {
        throw 'Este script está destinado a Windows 10.'
    }
}

function Get-RegistrySnapshot {
    param([string]$Path, [string]$Name)
    $exists = Test-Path -LiteralPath $Path
    $valueExists = $false
    $value = $null
    $kind = $null
    if ($exists) {
        $key = Get-Item -LiteralPath $Path
        $valueExists = $key.GetValueNames() -contains $Name
        if ($valueExists) {
            $value = $key.GetValue($Name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
            $kind = $key.GetValueKind($Name).ToString()
        }
    }
    [pscustomobject]@{ Path = $Path; Name = $Name; KeyExisted = $exists; ValueExisted = $valueExists; Value = $value; Kind = $kind }
}

function Set-DwordValue {
    param([string]$Path, [string]$Name, [int]$Value)
    $oldValue = '<no existía>'
    if ((Test-Path -LiteralPath $Path) -and ((Get-Item -LiteralPath $Path).GetValueNames() -contains $Name)) {
        $oldValue = (Get-ItemProperty -LiteralPath $Path -Name $Name).$Name
    }
    try {
        if (-not (Test-Path -LiteralPath $Path)) { New-Item -Path $Path -Force | Out-Null }
        New-ItemProperty -LiteralPath $Path -Name $Name -PropertyType DWord -Value $Value -Force | Out-Null
        Write-ChangeLog -Target "$Path\$Name" -Before ([string]$oldValue) -After ([string]$Value)
    } catch {
        Write-ChangeLog -Target "$Path\$Name" -Before ([string]$oldValue) -After ([string]$Value) -Result "Error: $($_.Exception.Message)"
        throw
    }
}

function Get-OneDriveInfo {
    $uninstallRoots = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'
    )
    $oneDriveEntry = $null
    foreach ($root in $uninstallRoots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $oneDriveEntry = Get-ChildItem -LiteralPath $root -ErrorAction SilentlyContinue |
            ForEach-Object { Get-ItemProperty -LiteralPath $_.PSPath -ErrorAction SilentlyContinue } |
            Where-Object { $_.DisplayName -match '^Microsoft OneDrive($|\s)' } |
            Select-Object -First 1
        if ($oneDriveEntry) { break }
    }
    $setupCandidates = @(
        (Join-Path $env:SystemRoot 'SysWOW64\OneDriveSetup.exe'),
        (Join-Path $env:SystemRoot 'System32\OneDriveSetup.exe'),
        (Join-Path $env:LOCALAPPDATA 'Microsoft\OneDrive\Update\OneDriveSetup.exe')
    )
    $setup = $setupCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    [pscustomobject]@{
        Installed = [bool]$oneDriveEntry
        UninstallString = if ($oneDriveEntry) { [string]$oneDriveEntry.UninstallString } else { '' }
        SetupPath = if ($setup) { [string]$setup } else { '' }
    }
}

function Restore-RegistryValue {
    param($Entry)
    $current = Get-RegistrySnapshot -Path $Entry.Path -Name $Entry.Name
    $before = if ($current.ValueExisted) { [string]$current.Value } else { '<no existía>' }
    $after = if ($Entry.ValueExisted) { [string]$Entry.Value } else { '<eliminado>' }
    try {
        if ($Entry.ValueExisted) {
            if (-not (Test-Path -LiteralPath $Entry.Path)) { New-Item -Path $Entry.Path -Force | Out-Null }
            $kind = [Microsoft.Win32.RegistryValueKind]::$($Entry.Kind)
            New-ItemProperty -LiteralPath $Entry.Path -Name $Entry.Name -PropertyType $kind -Value $Entry.Value -Force | Out-Null
        } elseif (Test-Path -LiteralPath $Entry.Path) {
            Remove-ItemProperty -LiteralPath $Entry.Path -Name $Entry.Name -ErrorAction SilentlyContinue
            if (-not $Entry.KeyExisted) {
                $key = Get-Item -LiteralPath $Entry.Path
                if ($key.GetValueNames().Count -eq 0 -and $key.SubKeyCount -eq 0) {
                    Remove-Item -LiteralPath $Entry.Path -Force -ErrorAction SilentlyContinue
                }
            }
        }
        Write-ChangeLog -Target "$($Entry.Path)\$($Entry.Name)" -Before $before -After $after -Result 'Restaurado'
    } catch {
        Write-ChangeLog -Target "$($Entry.Path)\$($Entry.Name)" -Before $before -After $after -Result "Error al restaurar: $($_.Exception.Message)"
        throw
    }
}

function Get-ServiceSnapshot {
    param([string]$Name)
    $service = Get-CimInstance Win32_Service -Filter "Name='$Name'" -ErrorAction SilentlyContinue
    if (-not $service) { return [pscustomobject]@{ Name = $Name; Exists = $false } }
    $serviceKey = "HKLM:\SYSTEM\CurrentControlSet\Services\$Name"
    [pscustomobject]@{
        Name = $Name; Exists = $true; WasRunning = ($service.State -eq 'Running')
        Start = (Get-ItemProperty -LiteralPath $serviceKey -Name Start).Start
        DelayedAutoStart = (Get-ItemProperty -LiteralPath $serviceKey -Name DelayedAutoStart -ErrorAction SilentlyContinue).DelayedAutoStart
        HadDelayedAutoStart = ((Get-Item -LiteralPath $serviceKey).GetValueNames() -contains 'DelayedAutoStart')
    }
}

function Save-Configuration {
    $registryTargets = @(
        @{ Path = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection'; Name = 'AllowTelemetry' },
        @{ Path = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Feeds'; Name = 'EnableFeeds' },
        @{ Path = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot'; Name = 'TurnOffWindowsCopilot' },
        @{ Path = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\GameDVR'; Name = 'AllowGameDVR' },
        @{ Path = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent'; Name = 'DisableWindowsConsumerFeatures' },
        @{ Path = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\OneDrive'; Name = 'DisableFileSyncNGSC' },
        @{ Path = 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR'; Name = 'AppCaptureEnabled' },
        @{ Path = 'HKCU:\System\GameConfigStore'; Name = 'GameDVR_Enabled' },
        @{ Path = 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Feeds'; Name = 'ShellFeedsTaskbarViewMode' },
        @{ Path = 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy'; Name = 'TailoredExperiencesWithDiagnosticDataEnabled' },
        @{ Path = 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo'; Name = 'Enabled' }
    )
    $services = @('DiagTrack', 'dmwappushservice', 'XblAuthManager', 'XblGameSave', 'XboxNetApiSvc', 'XboxGipSvc')
    [pscustomobject]@{
        Created = (Get-Date).ToString('o')
        Computer = $env:COMPUTERNAME
        User = [Security.Principal.WindowsIdentity]::GetCurrent().Name
        Registry = @($registryTargets | ForEach-Object { Get-RegistrySnapshot -Path $_.Path -Name $_.Name })
        Services = @($services | ForEach-Object { Get-ServiceSnapshot -Name $_ })
        OneDrive = (Get-OneDriveInfo)
    }
}

function New-SystemRestorePoint {
    try {
        Checkpoint-Computer -Description ("Optimizador Windows {0}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm')) -RestorePointType MODIFY_SETTINGS -ErrorAction Stop
        Write-ChangeLog -Target 'Punto de restauración del sistema' -Before '' -After 'Creado antes de aplicar ajustes'
    } catch {
        $recentPoint = $null
        try {
            $recentPoint = Get-CimInstance -Namespace 'root/default' -ClassName SystemRestore -ErrorAction Stop |
                ForEach-Object {
                    [pscustomobject]@{
                        Description = $_.Description
                        SequenceNumber = $_.SequenceNumber
                        Created = [System.Management.ManagementDateTimeConverter]::ToDateTime($_.CreationTime)
                    }
                } |
                Where-Object { $_.Created -le (Get-Date) -and $_.Created -ge (Get-Date).AddMinutes(-1440) } |
                Sort-Object Created -Descending |
                Select-Object -First 1
        } catch { }
        if ($recentPoint) {
            $pointInfo = "#$($recentPoint.SequenceNumber) '$($recentPoint.Description)' at $($recentPoint.Created.ToString('yyyy-MM-dd HH:mm:ss'))"
            Write-ChangeLog -Target 'Punto de restauración del sistema' -Before '' -After $pointInfo -Result 'Se reutilizó un punto reciente; Windows limita la creación a uno cada 24 horas'
            Write-Warning "Windows no permite crear otro punto durante 24 horas. Se usará el punto reciente $pointInfo como respaldo previo."
            return
        }
        Write-ChangeLog -Target 'Punto de restauración del sistema' -Before '' -After '' -Result "Error; cambios cancelados: $($_.Exception.Message)"
        throw "No se pudo crear el punto de restauración; no se aplicaron los ajustes. Activa Protección del sistema o inténtalo cuando Windows permita crear otro punto. Detalle: $($_.Exception.Message)"
    }
}

function Remove-OneDrive {
    param($OneDrive)
    if (-not $OneDrive.Installed) {
        Write-ChangeLog -Target 'Microsoft OneDrive' -Before 'No instalado' -After 'Sin cambios' -Result 'Omitido'
        return
    }
    if ([string]::IsNullOrWhiteSpace($OneDrive.UninstallString)) {
        Write-ChangeLog -Target 'Microsoft OneDrive' -Before 'Instalado' -After '' -Result 'Error: falta comando de desinstalación'
        throw 'Windows no proporcionó un comando de desinstalación para OneDrive; no se continuó.'
    }
    $uninstall = $OneDrive.UninstallString.Trim()
    if ($uninstall -match '^\s*(?:"([^"]+)"|(.+?\.exe))\s*(.*)$') {
        $exe = if ($Matches[1]) { $Matches[1] } else { $Matches[2] }
        $arguments = $Matches[3]
    }
    else { throw 'No se pudo interpretar el comando de desinstalación de OneDrive.' }
    if (-not (Test-Path -LiteralPath $exe)) { throw "No se encontró el desinstalador de OneDrive: $exe" }
    try {
        Stop-Process -Name OneDrive -Force -ErrorAction SilentlyContinue
        $process = Start-Process -FilePath $exe -ArgumentList $arguments -Wait -PassThru
        if ($process.ExitCode -ne 0) { throw "El desinstalador terminó con código $($process.ExitCode)." }
        Write-ChangeLog -Target 'Microsoft OneDrive' -Before 'Instalado' -After 'Desinstalado; archivos locales conservados'
    } catch {
        Write-ChangeLog -Target 'Microsoft OneDrive' -Before 'Instalado' -After '' -Result "Error: $($_.Exception.Message)"
        throw
    }
}

function Clear-OldTemporaryFiles {
    $cutoff = (Get-Date).AddDays(-7)
    $roots = @($env:TEMP, (Join-Path $env:windir 'Temp')) | Where-Object { $_ } | Select-Object -Unique
    $deletedCount = 0
    $deletedBytes = [long]0
    $skippedCount = 0

    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root -PathType Container)) {
            Write-ChangeLog -Target "Temporary folder $root" -Before '' -After '' -Result 'Not found; skipped'
            continue
        }
        $files = @(Get-ChildItem -LiteralPath $root -File -Force -Recurse -ErrorAction SilentlyContinue)
        foreach ($file in $files) {
            if ($file.LastWriteTime -ge $cutoff -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint)) { continue }
            if ($file.Name -like '~$*' -or $file.Extension -in @('.asd', '.wbk')) { continue }
            $size = [long]$file.Length
            try {
                Remove-Item -LiteralPath $file.FullName -Force -ErrorAction Stop
                $deletedCount++
                $deletedBytes += $size
                Write-ChangeLog -Target "Temporary file $($file.FullName)" -Before "$size bytes" -After 'Deleted (older than 7 days)'
            } catch {
                $skippedCount++
                Write-ChangeLog -Target "Temporary file $($file.FullName)" -Before "$size bytes" -After '' -Result "Skipped: $($_.Exception.Message)"
            }
        }

        $directories = @(Get-ChildItem -LiteralPath $root -Directory -Force -Recurse -ErrorAction SilentlyContinue | Sort-Object { $_.FullName.Length } -Descending)
        foreach ($directory in $directories) {
            if ($directory.LastWriteTime -ge $cutoff -or ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint)) { continue }
            try {
                $remaining = @(Get-ChildItem -LiteralPath $directory.FullName -Force -ErrorAction Stop)
                if ($remaining.Count -eq 0) {
                    Remove-Item -LiteralPath $directory.FullName -Force -ErrorAction Stop
                    Write-ChangeLog -Target "Temporary folder $($directory.FullName)" -Before 'Empty; older than 7 days' -After 'Removed'
                }
            } catch {
                $skippedCount++
                Write-ChangeLog -Target "Temporary folder $($directory.FullName)" -Before '' -After '' -Result "Skipped: $($_.Exception.Message)"
            }
        }
    }
    $megabytes = [math]::Round($deletedBytes / 1MB, 2)
    Write-ChangeLog -Target 'Temporary file cleanup' -Before '' -After "$deletedCount files; $megabytes MB released; $skippedCount skipped"
    Write-Host "Temporary cleanup: removed $deletedCount files ($megabytes MB); skipped $skippedCount locked or inaccessible items."
}

function Invoke-Apply {
    "Fecha`tResultado`tElemento`tValor anterior`tValor nuevo" | Set-Content -LiteralPath $LogPath -Encoding UTF8
    Write-ChangeLog -Target 'Equipo' -Before '' -After $env:COMPUTERNAME -Result 'Inicio de registro'
    $snapshot = Save-Configuration
    if (-not (Test-Path -LiteralPath $BackupDirectory)) { New-Item -ItemType Directory -Path $BackupDirectory -Force | Out-Null }
    if ($snapshot.OneDrive.SetupPath -and (Test-Path -LiteralPath $snapshot.OneDrive.SetupPath)) {
        $setupBackupPath = Join-Path $BackupDirectory 'OneDriveSetup.exe'
        Copy-Item -LiteralPath $snapshot.OneDrive.SetupPath -Destination $setupBackupPath -Force
        Add-Member -InputObject $snapshot.OneDrive -NotePropertyName SetupBackupPath -NotePropertyValue $setupBackupPath -Force
    } else {
        Add-Member -InputObject $snapshot.OneDrive -NotePropertyName SetupBackupPath -NotePropertyValue '' -Force
    }
    $backupPath = Join-Path $BackupDirectory ("antes-{0}.json" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
    $snapshot | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $backupPath -Encoding UTF8
    Write-Host "Respaldo de reversión: $backupPath" -ForegroundColor Cyan

    # El punto debe existir antes de desinstalar OneDrive o cambiar directivas y servicios.
    New-SystemRestorePoint
    Remove-OneDrive -OneDrive $snapshot.OneDrive

    # Mantener el nivel mínimo de datos de diagnóstico compatible con Windows 10.
    Set-DwordValue 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection' 'AllowTelemetry' 1
    Set-DwordValue 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy' 'TailoredExperiencesWithDiagnosticDataEnabled' 0
    Set-DwordValue 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo' 'Enabled' 0

    # Xbox/Game Bar y capturas de juego: desactivar sin desinstalar aplicaciones.
    Set-DwordValue 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\GameDVR' 'AllowGameDVR' 0
    Set-DwordValue 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR' 'AppCaptureEnabled' 0
    Set-DwordValue 'HKCU:\System\GameConfigStore' 'GameDVR_Enabled' 0

    # Noticias e intereses de Windows 10; la directiva de Copilot queda lista si está disponible.
    Set-DwordValue 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Feeds' 'EnableFeeds' 0
    Set-DwordValue 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Feeds' 'ShellFeedsTaskbarViewMode' 2
    Set-DwordValue 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot' 'TurnOffWindowsCopilot' 1
    Set-DwordValue 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent' 'DisableWindowsConsumerFeatures' 1
    Set-DwordValue 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\OneDrive' 'DisableFileSyncNGSC' 1

    foreach ($name in @('DiagTrack', 'dmwappushservice', 'XblAuthManager', 'XblGameSave', 'XboxNetApiSvc', 'XboxGipSvc')) {
        $serviceInfo = $snapshot.Services | Where-Object Name -eq $name
        if (-not $serviceInfo.Exists) {
            Write-ChangeLog -Target "Servicio $name" -Before '' -After '' -Result 'No presente; omitido'
            Write-Host "Servicio no presente: $name" -ForegroundColor DarkYellow
            continue
        }
        try {
            $previousState = (Get-Service -Name $name).Status.ToString()
            $previousStart = (Get-ItemProperty -LiteralPath "HKLM:\SYSTEM\CurrentControlSet\Services\$name" -Name Start).Start
            Stop-Service -Name $name -Force -ErrorAction SilentlyContinue
            Set-ItemProperty -LiteralPath "HKLM:\SYSTEM\CurrentControlSet\Services\$name" -Name Start -Value 4
            $currentState = (Get-Service -Name $name).Status.ToString()
            Write-ChangeLog -Target "Servicio $name (estado; inicio)" -Before "$previousState; $previousStart" -After "$currentState; 4 (deshabilitado)"
            Write-Host "Desactivado servicio prescindible seleccionado: $name"
        } catch {
            Write-ChangeLog -Target "Servicio $name" -Before '' -After '' -Result "Error: $($_.Exception.Message)"
            Write-Warning "No se pudo cambiar ${name}: $($_.Exception.Message)"
        }
    }
    Clear-OldTemporaryFiles
    Write-ChangeLog -Target 'Resultado' -Before '' -After 'Ajustes completados'
    Write-Host "Registro de cambios: $LogPath" -ForegroundColor Cyan
    Write-Host 'Listo. Reinicia Windows para aplicar las directivas. Defender y Windows Update no se modificaron.' -ForegroundColor Green
}

function Invoke-Restore {
    $files = @(Get-ChildItem -LiteralPath $BackupDirectory -Filter 'antes-*.json' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    if ($files.Count -eq 0) { throw "No hay respaldos en $BackupDirectory" }
    for ($i = 0; $i -lt $files.Count; $i++) { Write-Host ("{0}: {1}" -f ($i + 1), $files[$i].Name) }
    $choice = Read-Host 'Número de respaldo que quieres restaurar (Enter = el más reciente)'
    $selected = if ([string]::IsNullOrWhiteSpace($choice)) { $files[0] } else {
        $index = 0
        if (-not [int]::TryParse($choice, [ref]$index) -or $index -lt 1 -or $index -gt $files.Count) { throw 'Selección no válida.' }
        $files[$index - 1]
    }
    $snapshot = Get-Content -LiteralPath $selected.FullName -Raw | ConvertFrom-Json
    "Fecha`tResultado`tElemento`tValor anterior`tValor nuevo" | Set-Content -LiteralPath $LogPath -Encoding UTF8
    Write-ChangeLog -Target 'Respaldo' -Before '' -After $selected.Name -Result 'Inicio de restauración'
    New-SystemRestorePoint
    foreach ($entry in $snapshot.Registry) { Restore-RegistryValue $entry }
    foreach ($service in $snapshot.Services) {
        if (-not $service.Exists) { continue }
        $keyPath = "HKLM:\SYSTEM\CurrentControlSet\Services\$($service.Name)"
        $beforeStart = (Get-ItemProperty -LiteralPath $keyPath -Name Start).Start
        $beforeState = (Get-Service -Name $service.Name).Status.ToString()
        try {
            Set-ItemProperty -LiteralPath $keyPath -Name Start -Value ([int]$service.Start)
            if ($service.HadDelayedAutoStart) {
                Set-ItemProperty -LiteralPath $keyPath -Name DelayedAutoStart -Value ([int]$service.DelayedAutoStart)
            } else {
                Remove-ItemProperty -LiteralPath $keyPath -Name DelayedAutoStart -ErrorAction SilentlyContinue
            }
            if ($service.WasRunning) { Start-Service -Name $service.Name -ErrorAction SilentlyContinue }
            $restoredState = (Get-Service -Name $service.Name).Status.ToString()
            Write-ChangeLog -Target "Servicio $($service.Name) (estado; inicio)" -Before "$beforeState; $beforeStart" -After "$restoredState; $($service.Start)" -Result 'Restaurado'
        } catch {
            Write-ChangeLog -Target "Servicio $($service.Name)" -Before "$beforeState; $beforeStart" -After '' -Result "Error al restaurar: $($_.Exception.Message)"
            throw
        }
    }
    if ($snapshot.OneDrive.Installed -and -not (Get-OneDriveInfo).Installed) {
        if ($snapshot.OneDrive.SetupBackupPath -and (Test-Path -LiteralPath $snapshot.OneDrive.SetupBackupPath)) {
            $installer = $snapshot.OneDrive.SetupBackupPath
        } else {
            $installer = ''
        }
        if ($installer) {
            $process = Start-Process -FilePath $installer -ArgumentList '/install' -Wait -PassThru
            if ($process.ExitCode -eq 0) {
                Write-ChangeLog -Target 'Microsoft OneDrive' -Before 'Desinstalado' -After 'Reinstalado' -Result 'Restaurado'
            } else {
                Write-ChangeLog -Target 'Microsoft OneDrive' -Before 'Desinstalado' -After '' -Result "Error al reinstalar (código $($process.ExitCode))"
            }
        } else {
            Write-ChangeLog -Target 'Microsoft OneDrive' -Before 'Desinstalado' -After '' -Result 'Reinstalación manual necesaria; no se encontró instalador local'
        }
    }
    Write-ChangeLog -Target 'Resultado' -Before '' -After 'Restauración completada' -Result 'Restaurado'
    Write-Host "Registro de cambios: $LogPath" -ForegroundColor Cyan
    Write-Host "Configuración restaurada desde $($selected.Name). Reinicia Windows." -ForegroundColor Green
}

try {
    Assert-Windows10
    if (-not (Test-Administrator)) { throw 'Abre PowerShell como administrador y ejecuta de nuevo.' }
    switch ($Accion) {
        'Aplicar' { Invoke-Apply }
        'Restaurar' { Invoke-Restore }
        default {
            Write-Host 'Optimizador conservador de Windows 10' -ForegroundColor Cyan
            Write-Host '1. Aplicar ajustes reversibles (respaldará la configuración actual)'
            Write-Host '2. Restaurar un respaldo'
            $selection = Read-Host 'Elige 1 o 2'
            if ($selection -eq '1') { Invoke-Apply }
            elseif ($selection -eq '2') { Invoke-Restore }
            else { Write-Host 'Sin cambios.' }
        }
    }
} catch {
    Write-Error $_
    exit 1
}
