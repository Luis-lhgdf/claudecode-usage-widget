<#
.SYNOPSIS
    Faz o widget abrir junto com o Windows.

.DESCRIPTION
    Cria um atalho para run_widget.pyw na pasta Inicializar do usuario. Usa
    pythonw.exe, entao nenhuma janela de console aparece.

.PARAMETER Remove
    Remove o atalho em vez de criar.

.EXAMPLE
    .\scripts\install-startup.ps1
    .\scripts\install-startup.ps1 -Remove
#>
[CmdletBinding()]
param([switch]$Remove)

$ErrorActionPreference = "Stop"

$startup = [Environment]::GetFolderPath("Startup")
$shortcut = Join-Path $startup "CC Widget.lnk"

if ($Remove) {
    if (Test-Path $shortcut) {
        Remove-Item $shortcut -Force
        Write-Host "Atalho removido da inicializacao." -ForegroundColor Green
    } else {
        Write-Host "Nenhum atalho encontrado." -ForegroundColor DarkGray
    }
    exit 0
}

$repo = Split-Path -Parent $PSScriptRoot
$target = Join-Path $repo "run_widget.pyw"
if (-not (Test-Path $target)) {
    throw "run_widget.pyw nao encontrado em $repo"
}

# pythonw roda sem console; sem ele, um terminal preto fica aberto o tempo todo.
$pythonw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) { throw "python nao encontrado no PATH." }
    $pythonw = Join-Path (Split-Path $python) "pythonw.exe"
    if (-not (Test-Path $pythonw)) { throw "pythonw.exe nao encontrado ao lado de $python" }
}

$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($shortcut)
$link.TargetPath = $pythonw
$link.Arguments = "`"$target`""
$link.WorkingDirectory = $repo
$link.Description = "CC Widget - uso do Claude Code"
$link.Save()

Write-Host ""
Write-Host "Atalho criado na inicializacao:" -ForegroundColor Green
Write-Host "  $shortcut" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Para abrir agora:  Start-Process `"$pythonw`" -ArgumentList `"$target`""
