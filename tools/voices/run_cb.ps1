# Launch a Chatterbox job detached, logging to tools/voices/work/<name>.log
# usage: powershell -File tools/voices/run_cb.ps1 compare|roster [ids...]
# $env:CB_PY overrides the Python that has torch+CUDA+chatterbox-tts (default: the CitySteps Speech Studio venv, reused read-only).
param([Parameter(ValueFromRemainingArguments = $true)] [string[]] $JobArgs)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = $env:CB_PY
if (-not $py) { $py = Join-Path $env:USERPROFILE 'Documents\CitySteps - Claude CoWork\CitySteps Speech Studio\.venv\Scripts\python.exe' }
$env:PYTHONDONTWRITEBYTECODE = '1'
$name = if ($JobArgs.Count -gt 0) { $JobArgs[0] } else { 'compare' }
$log = Join-Path $here ("work\" + $name + ".log")
$argl = @('-P', '-u', ('"' + (Join-Path $here 'make_expressive.py') + '"')) + ($JobArgs | ForEach-Object { '"' + $_ + '"' })
Start-Process -FilePath $py -ArgumentList $argl -RedirectStandardOutput $log -RedirectStandardError ($log + '.err') -WindowStyle Hidden
Write-Output "started $name -> $log"
