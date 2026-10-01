[CmdletBinding()]
param(
    [Parameter()]
    [ValidateSet("User", "Project", "Both")]
    [string]$Scope = "Both",

    [Parameter()]
    [string]$ProjectRoot
)

$ErrorActionPreference = "Stop"

$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillName = "agent-builder"
$Files = @("SKILL.md", "README.md", "Install-AgentBuilder.ps1")

function Resolve-ProjectRoot {
    param([string]$ExplicitRoot)

    if ($ExplicitRoot) {
        return (Resolve-Path -LiteralPath $ExplicitRoot).Path
    }

    try {
        $gitRoot = (& git rev-parse --show-toplevel 2>$null)
        if ($LASTEXITCODE -eq 0 -and $gitRoot) {
            return (Resolve-Path -LiteralPath $gitRoot.Trim()).Path
        }
    }
    catch {
        # Fall back to the current directory.
    }

    return (Get-Location).Path
}

function Install-AgentBuilder {
    param(
        [Parameter(Mandatory)]
        [string]$DestinationRoot,

        [Parameter(Mandatory)]
        [string]$Label
    )

    $Destination = Join-Path $DestinationRoot ".claude\skills\$SkillName"

    $resolvedSource = [System.IO.Path]::GetFullPath($SourceDir).TrimEnd('\')
    $resolvedDestination = [System.IO.Path]::GetFullPath($Destination).TrimEnd('\')

    if ($resolvedSource -ieq $resolvedDestination) {
        Write-Host "[$Label] Source is this folder; nothing to copy: $Destination"
        return
    }

    New-Item -ItemType Directory -Force -Path $Destination | Out-Null

    foreach ($file in $Files) {
        $src = Join-Path $SourceDir $file
        if (Test-Path -LiteralPath $src) {
            Copy-Item -LiteralPath $src -Destination (Join-Path $Destination $file) -Force
        }
    }

    Write-Host "[$Label] Installed: $Destination"
}

if ($Scope -eq "User" -or $Scope -eq "Both") {
    $userRoot = if ($env:USERPROFILE) { $env:USERPROFILE } else { $HOME }
    if (-not $userRoot) {
        throw "USERPROFILE/HOME is not set; cannot determine the user Claude directory."
    }
    Install-AgentBuilder -DestinationRoot $userRoot -Label "User"
}

if ($Scope -eq "Project" -or $Scope -eq "Both") {
    $root = Resolve-ProjectRoot -ExplicitRoot $ProjectRoot
    Install-AgentBuilder -DestinationRoot $root -Label "Project"
}

Write-Host ""
Write-Host "Use inside Claude Code: /agent-builder"
Write-Host "If this skill directory did not exist when the current Claude Code session started, restart Claude Code once."
