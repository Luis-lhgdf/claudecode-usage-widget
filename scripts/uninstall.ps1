<#
.SYNOPSIS
    Desinstala o CC Widget.

.DESCRIPTION
    Fecha o widget, remove os atalhos da pasta Inicializar e da area de
    trabalho, e limpa a versao registrada.

    As preferencias em ~/.ccwidget/config.json ficam onde estao, para uma
    reinstalacao devolver o widget do jeito que voce deixou. Use -Tudo para
    apagar a pasta inteira.

.PARAMETER Tudo
    Apaga tambem ~/.ccwidget (preferencias e ultimo resultado do /usage).

.PARAMETER NoPause
    Nao espera Enter no fim. Util ao chamar de outro script.

.EXAMPLE
    .\scripts\uninstall.ps1
    .\scripts\uninstall.ps1 -Tudo
#>
[CmdletBinding()]
param([switch]$Tudo, [switch]$NoPause)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_shared.ps1")


Invoke-ComRelatorio -NoPause:$NoPause -Corpo {
    Write-Host ""

    $fechados = Stop-Widget
    if ($fechados) {
        Write-Host "Widget fechado." -ForegroundColor DarkGray
    }

    $removidos = 0
    foreach ($a in (Get-Atalhos)) {
        if (Test-Path $a.Caminho) {
            Remove-Item $a.Caminho -Force
            Write-Host "Atalho removido de $($a.Nome)." -ForegroundColor Green
            $removidos++
        }
    }
    if (-not $removidos) {
        Write-Host "Nenhum atalho encontrado." -ForegroundColor DarkGray
    }

    $pasta = Split-Path (Get-ConfigPath)
    if ($Tudo) {
        if (Test-Path $pasta) {
            Remove-Item $pasta -Recurse -Force
            Write-Host "Preferencias apagadas ($pasta)." -ForegroundColor Green
        }
    } else {
        Set-VersaoInstalada -Versao $null
        Write-Host ""
        Write-Host "Preferencias mantidas em $pasta" -ForegroundColor DarkGray
        Write-Host "Use -Tudo para apagar tambem." -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "Desinstalado." -ForegroundColor Green
}
