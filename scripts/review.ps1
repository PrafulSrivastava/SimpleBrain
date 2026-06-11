<#
.SYNOPSIS
    Launches a Pi review session using claude-opus-4.6 on amazon-bedrock,
    then restores claude-sonnet-4.6 when the session ends.

.DESCRIPTION
    1. Backs up current Pi model settings
    2. Switches to claude-opus-4.6 (amazon-bedrock) in ~/.pi/agent/settings.json
    3. Launches Pi interactively with the review prompt (in current terminal)
    4. Restores original model settings when Pi exits (even on crash/Ctrl+C)

.EXAMPLE
    .\scripts\review.ps1
#>

param()

# --- Paths ---
$ProjectRoot  = Split-Path $PSScriptRoot -Parent
$SettingsPath = Join-Path $env:USERPROFILE ".pi\agent\settings.json"
$PromptFile   = "scripts/prompts/review.md"
$ReviewModel  = "claude-opus-4-5"
$ReviewProvider = "amazon-bedrock"
$DefaultModel   = "claude-sonnet-4-5"
$DefaultProvider = "amazon-bedrock"

# --- Validate settings file exists ---
if (-not (Test-Path $SettingsPath)) {
    Write-Host ""
    Write-Host "  ERROR: Pi settings not found at $SettingsPath" -ForegroundColor Red
    Write-Host "  Make sure Pi is installed and has been run at least once." -ForegroundColor Yellow
    exit 1
}

# --- Validate prompt file exists ---
$PromptFullPath = Join-Path $ProjectRoot $PromptFile
if (-not (Test-Path $PromptFullPath)) {
    Write-Host ""
    Write-Host "  ERROR: Review prompt not found at $PromptFullPath" -ForegroundColor Red
    exit 1
}

# --- Read current settings ---
$settings = Get-Content $SettingsPath -Raw | ConvertFrom-Json
$originalProvider = $settings.defaultProvider
$originalModel    = $settings.defaultModel

Write-Host ""
Write-Host "  SimpleBrain - Implementation Review" -ForegroundColor Cyan
Write-Host "  ------------------------------------" -ForegroundColor DarkGray
Write-Host "  Current model  : $originalProvider / $originalModel" -ForegroundColor Gray
Write-Host "  Review model   : $ReviewProvider / $ReviewModel" -ForegroundColor Yellow
Write-Host "  Prompt         : $PromptFile" -ForegroundColor Gray
Write-Host ""

# --- Switch to review model ---
function Set-PiModel($provider, $model) {
    $s = Get-Content $SettingsPath -Raw | ConvertFrom-Json
    $s.defaultProvider = $provider
    $s.defaultModel    = $model
    $json = $s | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($SettingsPath, $json, [System.Text.UTF8Encoding]::new($false))
}

Write-Host "  Switching to claude-opus-4.6 (amazon-bedrock)..." -ForegroundColor Yellow
Set-PiModel $ReviewProvider $ReviewModel
Write-Host "  Model switched. Starting review..." -ForegroundColor Green
Write-Host ""

# --- Run Pi - use try/finally to guarantee model restore ---
Set-Location $ProjectRoot

try {
    & pi "--name" "simplebrain-review" "@$PromptFile"
} finally {
    # --- Always restore original model, even if Pi crashed or user hit Ctrl+C ---
    Write-Host ""
    Write-Host "  Review session ended. Restoring claude-sonnet-4.6 (amazon-bedrock)..." -ForegroundColor Yellow
    Set-PiModel $DefaultProvider $DefaultModel

    # Verify restore
    $restored = Get-Content $SettingsPath -Raw | ConvertFrom-Json
    if ($restored.defaultModel -eq $DefaultModel) {
        Write-Host "  Model restored: $($restored.defaultProvider) / $($restored.defaultModel)" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Could not verify model restore. Check $SettingsPath manually." -ForegroundColor Red
        Write-Host "  Expected: $DefaultProvider / $DefaultModel" -ForegroundColor Red
        Write-Host "  Got     : $($restored.defaultProvider) / $($restored.defaultModel)" -ForegroundColor Red
    }

    # Show review output location if it was written
    $reviewFile = Join-Path $ProjectRoot "docs\superpowers\reviews\2026-06-11-simplebrain-review.md"
    if (Test-Path $reviewFile) {
        Write-Host ""
        Write-Host "  Review saved to:" -ForegroundColor Cyan
        Write-Host "  $reviewFile" -ForegroundColor White
    }

    Write-Host ""
}
