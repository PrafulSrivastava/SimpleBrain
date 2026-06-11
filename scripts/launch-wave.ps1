<#
.SYNOPSIS
    SimpleBrain parallel agent launcher for Windows Terminal.

.DESCRIPTION
    Launches Pi agents in parallel Windows Terminal tabs for a given wave.
    Each agent receives a task-specific prompt file and shares a central
    _agent_comms.json for status tracking and inter-agent messaging.

.PARAMETER Wave
    The wave number to launch (1-7).

.PARAMETER Check
    Print wave status from _agent_comms.json without launching anything.

.EXAMPLE
    .\scripts\launch-wave.ps1 -Check
    .\scripts\launch-wave.ps1 -Wave 3

.NOTES
    Wave order:
      Wave 1: T1  (scaffold)
      Wave 2: T2  (config)
      Wave 3: T3, T5, T6, T7  (queue + pipeline + stores)
      Wave 4: T4, T8, T10     (ingest + file stage + healer)
      Wave 5: T9, T13         (worker + setup)
      Wave 6: T11, T12        (mcp + api)
      Wave 7: T14             (entry point + readme)
#>

param(
    [int]$Wave = 0,
    [switch]$Check
)

# --- Paths ---
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$CommsFile   = Join-Path $ProjectRoot "_agent_comms.json"
$PromptsDir  = Join-Path $PSScriptRoot "prompts"
$RunDir      = Join-Path $PSScriptRoot ".run"

# --- Wave to Task map ---
$WaveMap = @{
    1 = @("T1")
    2 = @("T2")
    3 = @("T3", "T5", "T6", "T7")
    4 = @("T4", "T8", "T10")
    5 = @("T9", "T13")
    6 = @("T11", "T12")
    7 = @("T14")
}

# --- Task metadata ---
$TaskMeta = @{
    "T1"  = @{ Name = "Project Scaffold and Core Models" }
    "T2"  = @{ Name = "BrainConfig" }
    "T3"  = @{ Name = "File Queue" }
    "T4"  = @{ Name = "Raw Store and Ingest Service" }
    "T5"  = @{ Name = "Pipeline Transcribe" }
    "T6"  = @{ Name = "Pipeline Chunk and Tag" }
    "T7"  = @{ Name = "Knowledge Store and Index Store" }
    "T8"  = @{ Name = "Pipeline File Stage" }
    "T9"  = @{ Name = "Background Worker" }
    "T10" = @{ Name = "Self-Healer" }
    "T11" = @{ Name = "MCP Server" }
    "T12" = @{ Name = "FastAPI Web UI and REST API" }
    "T13" = @{ Name = "Setup Wizard" }
    "T14" = @{ Name = "Entry Point and README" }
}

# --- Load comms file ---
function Get-Comms {
    if (-not (Test-Path $CommsFile)) {
        Write-Error "_agent_comms.json not found at $CommsFile"
        exit 1
    }
    return Get-Content $CommsFile -Raw | ConvertFrom-Json
}

# --- Print status table ---
function Show-Status {
    $comms = Get-Comms
    Write-Host ""
    Write-Host "  SimpleBrain Agent Status" -ForegroundColor Cyan
    Write-Host "  --------------------------------------------------" -ForegroundColor DarkGray
    Write-Host ("  {0,-5} {1,-6} {2,-34} {3}" -f "Wave","Task","Name","Status") -ForegroundColor Gray
    Write-Host "  --------------------------------------------------" -ForegroundColor DarkGray

    for ($w = 1; $w -le 7; $w++) {
        foreach ($tid in $WaveMap[$w]) {
            $t      = $comms.tasks.$tid
            $status = $t.status
            $color  = switch ($status) {
                "complete" { "Green" }
                "running"  { "Yellow" }
                "failed"   { "Red" }
                default    { "DarkGray" }
            }
            $icon = switch ($status) {
                "complete" { "[DONE]" }
                "running"  { "[RUN] " }
                "failed"   { "[FAIL]" }
                default    { "[    ]" }
            }
            Write-Host ("  {0,-5} {1,-6} {2,-34} {3} {4}" -f $w, $tid, $t.name, $icon, $status) -ForegroundColor $color
        }
    }

    Write-Host ""

    $comms.messages | Select-Object -Last 5 | ForEach-Object {
        if ($_.text) {
            Write-Host ("  MSG [{0} -> {1}] {2}" -f $_.from, $_.to, $_.text) -ForegroundColor White
        }
    }
    Write-Host ""
}

# --- Check mode ---
if ($Check) {
    Show-Status
    exit 0
}

# --- Validate wave number ---
if ($Wave -lt 1 -or $Wave -gt 7) {
    Write-Host ""
    Write-Host "  Usage:" -ForegroundColor Yellow
    Write-Host "    .\scripts\launch-wave.ps1 -Wave <1-7>" -ForegroundColor Yellow
    Write-Host "    .\scripts\launch-wave.ps1 -Check" -ForegroundColor Yellow
    Write-Host ""
    Show-Status
    exit 1
}

# --- Check prior wave is complete ---
if ($Wave -gt 1) {
    $comms     = Get-Comms
    $priorWave = $Wave - 1
    $incomplete = @()
    foreach ($tid in $WaveMap[$priorWave]) {
        if ($comms.tasks.$tid.status -ne "complete") {
            $incomplete += $tid
        }
    }
    if ($incomplete.Count -gt 0) {
        Write-Host ""
        Write-Host "  [BLOCKED] Wave $Wave cannot start - Wave $priorWave not finished:" -ForegroundColor Red
        foreach ($tid in $incomplete) {
            Write-Host "    - $tid ($($TaskMeta[$tid].Name))" -ForegroundColor Red
        }
        Write-Host ""
        Write-Host "  Run -Check to see full status." -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
}

# --- Create working dirs ---
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

# --- Generate per-task run scripts and build wt command ---
$tasks   = $WaveMap[$Wave]
$wtParts = @()
$first   = $true

Write-Host ""
Write-Host "  Preparing Wave $Wave ($($tasks.Count) task(s))..." -ForegroundColor Cyan
Write-Host ""

foreach ($tid in $tasks) {
    $taskName   = $TaskMeta[$tid].Name
    $promptFile = Join-Path $PromptsDir "task-$tid.md"
    $runFile    = Join-Path $RunDir "task-$tid.ps1"

    # Verify prompt file exists
    if (-not (Test-Path $promptFile)) {
        Write-Warning "Prompt file missing: $promptFile - skipping $tid"
        continue
    }

    # Relative prompt path for pi (forward slashes)
    $relPrompt = "scripts/prompts/task-$tid.md"

    # Write the run script - use single-quoted strings to avoid $ expansion issues
    $runContent  = "Set-Location '$ProjectRoot'" + "`r`n"
    $runContent += 'Write-Host "  Task ' + $tid + ': ' + $taskName + '" -ForegroundColor Cyan' + "`r`n"
    $runContent += 'Write-Host "  Reading: ' + $relPrompt + '" -ForegroundColor DarkGray' + "`r`n"
    $runContent += 'Write-Host ""' + "`r`n"
    $runContent += "pi '@$relPrompt'" + "`r`n"

    Set-Content -Path $runFile -Value $runContent -Encoding UTF8

    Write-Host "  + $tid - $taskName" -ForegroundColor Green

    # Build wt tab entry
    $tabTitle = "$tid - $taskName"
    $tabCmd   = "powershell -NoExit -File `"$runFile`""

    if ($first) {
        $wtParts += "new-tab --title `"$tabTitle`" $tabCmd"
        $first = $false
    } else {
        $wtParts += "new-tab --title `"$tabTitle`" $tabCmd"
    }
}

if ($wtParts.Count -eq 0) {
    Write-Host ""
    Write-Host "  No tasks to launch. Check prompt files exist in scripts\prompts\" -ForegroundColor Red
    exit 1
}

# --- Launch Windows Terminal ---
$wtArgs = $wtParts -join " ; "

Write-Host ""
Write-Host "  Launching Windows Terminal with $($wtParts.Count) tab(s)..." -ForegroundColor Cyan

try {
    Start-Process "wt" -ArgumentList $wtArgs
    Write-Host "  Done. Each agent will:" -ForegroundColor Green
    Write-Host "    1. Read the plan and _agent_comms.json" -ForegroundColor Gray
    Write-Host "    2. Mark their task [running] in _agent_comms.json" -ForegroundColor Gray
    Write-Host "    3. Implement all steps and run tests" -ForegroundColor Gray
    Write-Host "    4. Mark their task [complete] in _agent_comms.json" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Monitor : .\scripts\launch-wave.ps1 -Check" -ForegroundColor Yellow
    if ($Wave -lt 7) {
        $next = $Wave + 1
        Write-Host "  Next    : .\scripts\launch-wave.ps1 -Wave $next  (after all Wave $Wave tasks show [DONE])" -ForegroundColor Yellow
    } else {
        Write-Host "  Final wave launched - SimpleBrain build in progress!" -ForegroundColor Magenta
    }
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "  ERROR: Could not launch Windows Terminal." -ForegroundColor Red
    Write-Host "  Make sure 'wt.exe' is on your PATH (install Windows Terminal from the Microsoft Store)." -ForegroundColor Red
    Write-Host ""
    Write-Host "  To run agents manually, execute these scripts in separate terminals:" -ForegroundColor Yellow
    foreach ($tid in $tasks) {
        $runFile = Join-Path $RunDir "task-$tid.ps1"
        Write-Host "    powershell -File `"$runFile`"" -ForegroundColor Gray
    }
}
