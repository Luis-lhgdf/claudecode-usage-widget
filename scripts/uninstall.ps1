<#
.SYNOPSIS
    Desinstala o CC Widget.

.DESCRIPTION
    Fecha o widget, remove o atalho da area de trabalho -- e o da pasta
    Inicializar, se sobrou de uma versao antiga -- e limpa a versao
    registrada.

    Aberto no terminal, pergunta o que fazer com as preferencias em
    ~/.ccwidget/config.json: manter, para uma reinstalacao devolver o widget
    do jeito que voce deixou, ou apagar a pasta inteira. Os parametros abaixo
    respondem de antemao e dispensam a pergunta -- e sem console para
    perguntar, as preferencias ficam.

.PARAMETER Tudo
    Apaga tambem ~/.ccwidget (preferencias e ultimo resultado do /usage).

.PARAMETER Manter
    Mantem ~/.ccwidget. Remove so o atalho e a versao registrada.

.PARAMETER NoPause
    Nao espera Enter no fim. Util ao chamar de outro script.

.EXAMPLE
    .\scripts\uninstall.ps1
    .\scripts\uninstall.ps1 -Tudo
    .\scripts\uninstall.ps1 -Manter
#>
[CmdletBinding()]
param([switch]$Tudo, [switch]$Manter, [switch]$NoPause)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_shared.ps1")


Invoke-ComRelatorio -NoPause:$NoPause -Corpo {
    if ($Tudo -and $Manter) {
        throw "-Tudo e -Manter pedem coisas opostas. Escolha um."
    }

    # A pergunta vem antes de qualquer mudanca: cancelar tem de deixar o
    # widget aberto e o atalho no lugar.
    $escolha = "manter"
    if ($Tudo) {
        $escolha = "tudo"
    } elseif (-not $Manter -and (Test-Interativo)) {
        $escolha = Read-EscolhaDesinstalar
    }

    if ($escolha -eq "cancelar") {
        Write-Host ""
        Write-Host "Cancelado. Nada foi removido." -ForegroundColor DarkGray
        return
    }

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
    # Instalacoes antigas punham um atalho na pasta Inicializar.
    foreach ($nome in (Remove-AtalhosLegado)) {
        Write-Host "Atalho removido de $nome." -ForegroundColor Green
        $removidos++
    }
    if (-not $removidos) {
        Write-Host "Nenhum atalho encontrado." -ForegroundColor DarkGray
    }

    $pasta = Split-Path (Get-ConfigPath)
    if ($escolha -eq "tudo") {
        if (Test-Path $pasta) {
            Remove-Item $pasta -Recurse -Force
            Write-Host "Preferencias apagadas ($pasta)." -ForegroundColor Green
        }
    } else {
        Set-VersaoInstalada -Versao $null
        Write-Host ""
        Write-Host "Preferencias mantidas em $pasta" -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "Desinstalado." -ForegroundColor Green
}
