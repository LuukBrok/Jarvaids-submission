$ErrorActionPreference = 'Stop'
$jarvaidsRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$jarvaidsData = Join-Path $jarvaidsRoot '.local\live-test'
$jarvaidsBackends = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object {
    $_.CommandLine -match '-m genai_server' -and $_.CommandLine.Contains($jarvaidsData)
}
$jarvaidsStopped = @{}
foreach ($jarvaidsBackend in $jarvaidsBackends) {
    $jarvaidsCurrent = $jarvaidsBackend
    for ($jarvaidsDepth = 0; $jarvaidsDepth -lt 5 -and $jarvaidsCurrent; $jarvaidsDepth++) {
        if ($jarvaidsCurrent.Name -eq 'python.exe' -and $jarvaidsCurrent.CommandLine -match 'local_test\.py[" ]+start') {
            $jarvaidsId = [int]$jarvaidsCurrent.ProcessId
            if (-not $jarvaidsStopped.ContainsKey($jarvaidsId)) {
                & taskkill /PID $jarvaidsId /T /F | Out-Null
                $jarvaidsStopped[$jarvaidsId] = $true
            }
            break
        }
        $jarvaidsCurrent = Get-CimInstance Win32_Process -Filter ("ProcessId = " + $jarvaidsCurrent.ParentProcessId) -ErrorAction SilentlyContinue
    }
}
if ($jarvaidsStopped.Count) { Write-Host 'Jarvaids stopped. Saved sessions remain in this folder.' }
else { Write-Host 'No Jarvaids launcher belonging to this folder was found.' }
