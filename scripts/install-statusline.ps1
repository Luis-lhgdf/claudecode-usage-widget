<#
.SYNOPSIS
    Instala a ponte de status line no Claude Code.

.DESCRIPTION
    Registra `statusLine` em ~/.claude/settings.json apontando para
    statusline_hook.py. A partir dai, cada atualizacao da interface do Claude
    Code grava os percentuais oficiais de limite em ~/.ccwidget/state.json,
    que e o que o widget mostra.

    Um backup do settings.json e criado antes de qualquer alteracao.
    Se ja existir uma statusLine configurada, o script avisa e nao sobrescreve
    sem o parametro -Force.

.PARAMETER Force
    Substitui uma statusLine ja existente.

.EXAMPLE
    .\scripts\install-statusline.ps1
#>
[CmdletBinding()]
param([switch]$Force)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$hook = Join-Path $repo "statusline_hook.py"
if (-not (Test-Path $hook)) {
    throw "statusline_hook.py nao encontrado em $repo"
}

# Python precisa estar no PATH; usamos o caminho absoluto para a status line
# funcionar mesmo se o PATH mudar.
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    throw "python nao encontrado no PATH. Instale o Python 3.10+ e tente de novo."
}

$settingsPath = Join-Path $HOME ".claude\settings.json"
if (Test-Path $settingsPath) {
    $raw = Get-Content $settingsPath -Raw -Encoding UTF8
    $settings = $raw | ConvertFrom-Json
    $backup = "$settingsPath.bak-$(Get-Date -Format yyyyMMdd-HHmmss)"
    Copy-Item $settingsPath $backup
    Write-Host "Backup criado: $backup" -ForegroundColor DarkGray
} else {
    New-Item -ItemType Directory -Force (Split-Path $settingsPath) | Out-Null
    $settings = [PSCustomObject]@{}
}

if ($settings.PSObject.Properties.Name -contains "statusLine" -and $null -ne $settings.statusLine -and -not $Force) {
    Write-Host ""
    Write-Host "Ja existe uma statusLine configurada:" -ForegroundColor Yellow
    Write-Host ($settings.statusLine | ConvertTo-Json -Compress)
    Write-Host ""
    Write-Host "Use -Force para substituir." -ForegroundColor Yellow
    exit 1
}

$command = "`"$python`" `"$hook`""
$statusLine = [PSCustomObject]@{
    type    = "command"
    command = $command
    padding = 0
}

if ($settings.PSObject.Properties.Name -contains "statusLine") {
    $settings.statusLine = $statusLine
} else {
    $settings | Add-Member -MemberType NoteProperty -Name statusLine -Value $statusLine
}

$settings | ConvertTo-Json -Depth 20 | Set-Content $settingsPath -Encoding UTF8

Write-Host ""
Write-Host "Status line instalada." -ForegroundColor Green
Write-Host "  comando: $command" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Abra uma nova sessao do Claude Code e envie uma mensagem." -ForegroundColor Cyan
Write-Host "Os percentuais oficiais aparecem depois da primeira resposta da API."
Write-Host ""
Write-Host "Para conferir:  python -m ccwidget report"
