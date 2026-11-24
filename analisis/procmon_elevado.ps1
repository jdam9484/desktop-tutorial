# Se ejecuta elevado. Captura con Process Monitor hasta que aparezca el archivo fin.flag.
$b = $PSScriptRoot + "\pm"; New-Item -ItemType Directory -Force $b | Out-Null
$p = Join-Path (Split-Path $PSScriptRoot) "herramientas\procmon\Procmon64.exe"
Start-Process $p -ArgumentList "/AcceptEula /Quiet /Minimized /BackingFile `"$b\c.pml`""
Start-Process $p -ArgumentList "/WaitForIdle" -Wait
New-Item "$b\listo.flag" -ItemType File -Force | Out-Null
$t = 0; while (-not (Test-Path "$b\fin.flag") -and $t -lt 180) { Start-Sleep 1; $t++ }
Start-Process $p -ArgumentList "/Terminate" -Wait
Start-Process $p -ArgumentList "/AcceptEula /Quiet /OpenLog `"$b\c.pml`" /SaveAs `"$b\c.csv`"" -Wait
New-Item "$b\hecho.flag" -ItemType File -Force | Out-Null
