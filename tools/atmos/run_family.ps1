param([string]$names, [string]$log)
$root="C:\Users\Robert Walter-Joseph\Code Projects\squall-cove-large"
python -I "$root\tools\atmos\bake.py" $names *> $log
"FIN" | Add-Content $log
