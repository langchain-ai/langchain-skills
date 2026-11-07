param(
    [string]$Project = (Get-Location).Path,
    [ValidateSet('claude', 'codex', 'cursor', 'dcode', 'deepagents')]
    [string]$Agent = 'claude',
    [switch]$Global,
    [switch]$Link,
    [switch]$Force,
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'skills'
if (-not (Test-Path -LiteralPath $source -PathType Container)) {
    throw "Skills directory not found: $source"
}

if ($Global) {
    $homeDir = [Environment]::GetFolderPath('UserProfile')
    switch ($Agent) {
        'claude'     { $installDir = Join-Path $homeDir '.claude' }
        'codex'      { $installDir = Join-Path $homeDir '.codex' }
        'cursor'     { $installDir = Join-Path $homeDir '.cursor' }
        'dcode'      { $installDir = Join-Path $homeDir '.deepagents/agent' }
        'deepagents' { $installDir = Join-Path $homeDir '.deepagents/langchain_agent' }
    }
} else {
    switch ($Agent) {
        'claude'     { $installDir = Join-Path $Project '.claude' }
        'codex'      { $installDir = Join-Path $Project '.agents' }
        'cursor'     { $installDir = Join-Path $Project '.cursor' }
        'dcode'      { $installDir = Join-Path $Project '.deepagents' }
        'deepagents' { $installDir = Join-Path $Project '.deepagents' }
    }
}

$mode = if ($Link) { 'linked' } else { 'copied' }
Write-Host "Install $Agent skills to $installDir ($mode)"
if (-not $Yes) {
    $answer = Read-Host 'Proceed? [y/N]'
    if ($answer -notmatch '^[Yy]$') { return }
}

$skillsDir = Join-Path $installDir 'skills'
New-Item -ItemType Directory -Path $skillsDir -Force | Out-Null
foreach ($skill in Get-ChildItem -LiteralPath $source -Directory) {
    if (-not (Test-Path -LiteralPath (Join-Path $skill.FullName 'SKILL.md'))) {
        continue
    }
    $destination = Join-Path $skillsDir $skill.Name
    $existing = Get-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue
    if ($null -ne $existing) {
        if (-not $Force) {
            Write-Host "Skipped $($skill.Name) (exists; use -Force to replace)"
            continue
        }
        if ($existing.LinkType -eq 'SymbolicLink') {
            Remove-Item -LiteralPath $destination -Force
        } else {
            Remove-Item -LiteralPath $destination -Recurse -Force
        }
    }
    if ($Link) {
        try {
            New-Item -ItemType SymbolicLink -Path $destination -Target $skill.FullName -ErrorAction Stop | Out-Null
        } catch {
            throw "Could not create a symbolic link for $($skill.Name). Enable Windows Developer Mode or run again without -Link. $($_.Exception.Message)"
        }
    } else {
        Copy-Item -LiteralPath $skill.FullName -Destination $destination -Recurse
    }
    Write-Host "Installed $($skill.Name)"
}

if ($Agent -eq 'deepagents' -and $Global) {
    $persona = Join-Path $installDir 'AGENTS.md'
    if ((-not (Test-Path -LiteralPath $persona)) -or $Force) {
        $existingPersona = Get-Item -LiteralPath $persona -Force -ErrorAction SilentlyContinue
        if ($null -ne $existingPersona -and $existingPersona.LinkType -eq 'SymbolicLink') {
            Remove-Item -LiteralPath $persona -Force
        }
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'config/AGENTS.md') -Destination $persona -Force
        Write-Host 'Installed Deep Agents persona'
    } else {
        Write-Host 'Skipped AGENTS.md (exists; use -Force to replace)'
    }
}

Write-Host 'Done. Restart your agent session to load updated skills.'
if ($Link) {
    Write-Host 'After a git pull, existing links use updated skills. Rerun this installer to add new skills.'
} else {
    Write-Host 'After a git pull, rerun this installer with -Force to refresh copies.'
}
