# Windows Office Optimizer

A conservative, reversible PowerShell optimizer for Windows 10 office PCs. It keeps Microsoft Defender and Windows Update enabled.

Before applying **or restoring** settings, the script attempts to create a Windows System Restore point. If Windows enforces its 24-hour creation limit, the script reuses the latest existing point from the previous 24 hours. If neither a new nor recent point is available, it stops before making those changes. System Protection must be enabled.

The script also saves the previous settings under `respaldos/` and writes a timestamped `cambios-YYYYMMDD-HHMMSS.log` beside the script. The log records old and new registry values, service changes, restore-point creation, and errors.

## Changes

- Lowers diagnostic data to the minimum level supported by Windows 10 and disables tailored experiences and advertising.
- Disables Xbox Game Bar and game capture.
- Hides Windows 10 News and interests and disables consumer app suggestions.
- Stops and disables `DiagTrack`, `dmwappushservice`, and Xbox services when present.
- Uninstalls the OneDrive sync desktop app and blocks OneDrive sync. It does not delete the local OneDrive folder or cloud files. Browser access and webmail are unaffected.
- Leaves preinstalled apps installed because removing them does not have a reliable rollback on every PC.
- Does not change Defender, Windows Update, Search, SysMain, networking, audio, camera, or printing.

Windows 10 does not include Copilot as a standard feature. The script also writes its disable policy in case that feature is present.

Before uninstalling OneDrive, make sure files that are available only online are accessible from the browser or downloaded if they will be needed offline. Microsoft says uninstalling OneDrive does not delete cloud files; they remain available at OneDrive.com. [Microsoft OneDrive uninstall guidance](https://support.microsoft.com/en-us/onedrive/turn-off-disable-or-uninstall-onedrive)

## Run

1. Copy this folder to the Windows 10 PC.
2. Open PowerShell **as Administrator**, using the Windows account that uses the PC.
3. Change to this folder and run:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\win-office-optimizer.ps1
   ```

4. Choose `1` to apply the settings. The script writes a backup before changing Windows.
5. Restart Windows.

To apply the settings directly, pass `-Accion Aplicar`. To open the restore menu directly, pass `-Accion Restaurar`. The default menu and prompts are currently in Spanish.

## Restore

Run the script again as Administrator and choose `2`. Select the backup to restore; press Enter to use the newest one. Restart afterward.

The backup includes the current user's preferences and the previous startup settings for the selected services. If a OneDrive installer is found on the PC, a copy is also stored under `respaldos/` so the restore action can reinstall it. Keep that folder beside the script.

System Restore reverts Windows system files and settings; it is not a substitute for a separate backup of important personal data. The script does not delete the local OneDrive folder or cloud files.
