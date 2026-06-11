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
    # Check current status
    .\scripts\launch-wave.ps1 -Check

    # Launch wave 3 (4 parallel agents)
    .\scripts\launch-wave.ps1 -Wave 3

.NOTES
    Wave dependency order:
      Wave 1: T1  (scaffold)
      Wave 2: T2  (config)
      Wave 3: T3, T5, T6, T7  (queue + pipeline stages + stores)
      Wave 4: T4, T8, T10     (ingest service + file stage + healer)
      Wave 5: T9, T13         (worker + setup)
      Wave 6: T11, T12        (mcp + api)
      Wave 7: T14             (entry point + readme)

    Prerequisites: Windows Terminal (wt.exe) and Pi CLI (pi) on PATH.
#>

param(
    [int]$Wave = 0,
    [switch]$Check
)

# ── Paths ──────────────────────────────────────────────────────────────────────
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$CommsFile   = Join-Path $ProjectRoot "_agent_comms.json"
$PromptsDir  = Join-Path $PSScriptRoot ".prompts"
$RunDir      = Join-Path $PSScriptRoot ".run"

# ── Wave → Task map ────────────────────────────────────────────────────────────
$WaveMap = @{
    1 = @("T1")
    2 = @("T2")
    3 = @("T3", "T5", "T6", "T7")
    4 = @("T4", "T8", "T10")
    5 = @("T9", "T13")
    6 = @("T11", "T12")
    7 = @("T14")
}

# ── Task metadata ──────────────────────────────────────────────────────────────
$TaskMeta = @{
    "T1"  = @{ Name = "Project Scaffold & Core Models"; Section = "## Task 1:"  }
    "T2"  = @{ Name = "BrainConfig";                   Section = "## Task 2:"  }
    "T3"  = @{ Name = "File Queue";                    Section = "## Task 3:"  }
    "T4"  = @{ Name = "Raw Store & Ingest Service";    Section = "## Task 4:"  }
    "T5"  = @{ Name = "Pipeline - Transcribe";         Section = "## Task 5:"  }
    "T6"  = @{ Name = "Pipeline - Chunk & Tag";        Section = "## Task 6:"  }
    "T7"  = @{ Name = "Knowledge Store & Index Store"; Section = "## Task 7:"  }
    "T8"  = @{ Name = "Pipeline File Stage";           Section = "## Task 8:"  }
    "T9"  = @{ Name = "Background Worker";             Section = "## Task 9:"  }
    "T10" = @{ Name = "Self-Healer";                   Section = "## Task 10:" }
    "T11" = @{ Name = "MCP Server";                    Section = "## Task 11:" }
    "T12" = @{ Name = "FastAPI Web UI & REST API";     Section = "## Task 12:" }
    "T13" = @{ Name = "Setup Wizard";                  Section = "## Task 13:" }
    "T14" = @{ Name = "Entry Point & README";          Section = "## Task 14:" }
}

# ── Helper: load comms file ────────────────────────────────────────────────────
function Get-Comms {
    if (-not (Test-Path $CommsFile)) {
        Write-Error "_agent_comms.json not found at $CommsFile"
        exit 1
    }
    return Get-Content $CommsFile -Raw | ConvertFrom-Json
}

# ── Helper: save comms file ────────────────────────────────────────────────────
function Save-Comms($comms) {
    $comms | ConvertTo-Json -Depth 10 | Set-Content $CommsFile -Encoding UTF8
}

# ── Helper: print status table ─────────────────────────────────────────────────
function Show-Status {
    $comms = Get-Comms
    Write-Host ""
    Write-Host "  SimpleBrain Agent Comms Status" -ForegroundColor Cyan
    Write-Host "  ─────────────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host ("  {0,-5} {1,-6} {2,-32} {3}" -f "Wave","Task","Name","Status") -ForegroundColor Gray
    Write-Host "  ─────────────────────────────────────────────────────" -ForegroundColor DarkGray

    for ($w = 1; $w -le 7; $w++) {
        foreach ($tid in $WaveMap[$w]) {
            $t = $comms.tasks.$tid
            $status = $t.status
            $color = switch ($status) {
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
            Write-Host ("  {0,-5} {1,-6} {2,-32} {3} {4}" -f $w, $tid, $t.name, $icon, $status) -ForegroundColor $color
        }
    }

    Write-Host ""
    if ($comms.messages.Count -gt 0) {
        Write-Host "  Recent Messages:" -ForegroundColor Cyan
        $comms.messages | Select-Object -Last 5 | ForEach-Object {
            Write-Host "  [$($_.from) → $($_.to)] $($_.text)" -ForegroundColor White
        }
    }
    Write-Host ""
}

# ── -Check mode ────────────────────────────────────────────────────────────────
if ($Check) {
    Show-Status
    exit 0
}

# ── Validate wave ──────────────────────────────────────────────────────────────
if ($Wave -lt 1 -or $Wave -gt 7) {
    Write-Host ""
    Write-Host "  Usage: .\scripts\launch-wave.ps1 -Wave <1-7>" -ForegroundColor Yellow
    Write-Host "         .\scripts\launch-wave.ps1 -Check" -ForegroundColor Yellow
    Write-Host ""
    Show-Status
    exit 1
}

# ── Check prerequisites: prior waves must be complete ─────────────────────────
if ($Wave -gt 1) {
    $comms = Get-Comms
    $priorWave = $Wave - 1
    $priorTasks = $WaveMap[$priorWave]
    $incomplete = @()
    foreach ($tid in $priorTasks) {
        if ($comms.tasks.$tid.status -ne "complete") {
            $incomplete += $tid
        }
    }
    if ($incomplete.Count -gt 0) {
        Write-Host ""
        Write-Host "  [BLOCKED] Wave $Wave cannot start — Wave $priorWave tasks not complete:" -ForegroundColor Red
        $incomplete | ForEach-Object { Write-Host "    - $_ ($($TaskMeta[$_].Name))" -ForegroundColor Red }
        Write-Host ""
        Write-Host "  Run -Check to see full status." -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
}

# ── Create dirs ────────────────────────────────────────────────────────────────
New-Item -ItemType Directory -Force -Path $PromptsDir | Out-Null
New-Item -ItemType Directory -Force -Path $RunDir      | Out-Null

# ── Generate prompt files and run scripts ─────────────────────────────────────
$tasks = $WaveMap[$Wave]

Write-Host ""
Write-Host "  Generating prompts for Wave $Wave ($($tasks.Count) tasks)..." -ForegroundColor Cyan

foreach ($tid in $tasks) {
    $meta = $TaskMeta[$tid]
    $promptFile = Join-Path $PromptsDir "task-$tid.md"
    $runFile    = Join-Path $RunDir "task-$tid.ps1"

    # Read the prompt template and write it
    $promptContent = Get-Content (Join-Path $PSScriptRoot "prompts\task-$tid.md") -Raw -ErrorAction SilentlyContinue
    if (-not $promptContent) {
        Write-Warning "Prompt file not found: scripts\prompts\task-$tid.md — skipping $tid"
        continue
    }

    # Write the run script (pi launcher)
    @"
# Auto-generated by launch-wave.ps1 — Task $tid: $($meta.Name)
Set-Location "$ProjectRoot"
Write-Host "  Starting Task $tid: $($meta.Name)" -ForegroundColor Cyan
Write-Host "  Comms file: _agent_comms.json" -ForegroundColor DarkGray
Write-Host ""
pi "@scripts\.prompts\task-$tid.md"
"@ | Set-Content $runFile -Encoding UTF8

    Write-Host "  + $tid ($($meta.Name))" -ForegroundColor Green
}

# ── Build and launch Windows Terminal command ──────────────────────────────────
Write-Host ""
Write-Host "  Launching Windows Terminal with $($tasks.Count) tab(s) for Wave $Wave..." -ForegroundColor Cyan

$wtParts = @()
$first = $true

foreach ($tid in $tasks) {
    $runFile = Join-Path $RunDir "task-$tid.ps1"
    if (-not (Test-Path $runFile)) { continue }

    $title = "$tid - $($TaskMeta[$tid].Name)"
    $cmd   = "powershell -NoExit -File `"$runFile`""

    if ($first) {
        $wtParts += "new-tab --title `"$title`" $cmd"
        $first = $false
    } else {
        $wtParts += "new-tab --title `"$title`" $cmd"
    }
}

$wtArgs = $wtParts -join " ; "

try {
    Start-Process "wt" -ArgumentList $wtArgs
    Write-Host "  Windows Terminal launched successfully." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Each agent will:" -ForegroundColor Gray
    Write-Host "    1. Read the plan and _agent_comms.json" -ForegroundColor Gray
    Write-Host "    2. Mark their task as [running] in _agent_comms.json" -ForegroundColor Gray
    Write-Host "    3. Implement all steps" -ForegroundColor Gray
    Write-Host "    4. Mark their task as [complete] in _agent_comms.json" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Monitor progress: .\scripts\launch-wave.ps1 -Check" -ForegroundColor Yellow
    Write-Host "  Launch next wave: .\scripts\launch-wave.ps1 -Wave $($Wave + 1)" -ForegroundColor Yellow
    Write-Host ""
} catch {
    Write-Error "Failed to launch Windows Terminal: $_"
    Write-Host "  Make sure 'wt' (Windows Terminal) is on your PATH." -ForegroundColor Red
}
