$ErrorActionPreference = 'Stop'

$command = 'cd /home/pdf-merge && if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi && python3 pdf.py'

$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = 'wsl.exe'
$psi.ArgumentList.Add('-d') | Out-Null
$psi.ArgumentList.Add('Debian') | Out-Null
$psi.ArgumentList.Add('-e') | Out-Null
$psi.ArgumentList.Add('/bin/bash') | Out-Null
$psi.ArgumentList.Add('-lc') | Out-Null
$psi.ArgumentList.Add($command) | Out-Null
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.WindowStyle = 'Hidden'

[System.Diagnostics.Process]::Start($psi) | Out-Null
