<#
.SYNOPSIS
    Instala o CC Widget.

.DESCRIPTION
    Cria dois atalhos para run_widget.pyw: um na pasta Inicializar, para o
    widget subir junto com o Windows, e outro na area de trabalho. Ambos usam
    pythonw.exe -- nenhuma janela de console aparece -- e levam o icone do
    mascote.

    Rodar de novo e seguro: o script compara a versao do repositorio com a que
    esta registrada na maquina e diz se e instalacao, atualizacao ou
    reinstalacao, substituindo os atalhos de qualquer forma.

    Ao terminar, abre o widget -- reiniciando a copia aberta quando a versao
    muda, para o que esta na tela ser a versao recem instalada.

.PARAMETER NoLaunch
    Nao abre o widget depois de instalar.

.PARAMETER NoPause
    Nao espera Enter no fim. Util ao chamar de outro script.

.EXAMPLE
    .\scripts\install.ps1
#>
[CmdletBinding()]
param([switch]$NoLaunch, [switch]$NoPause)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_shared.ps1")


Invoke-ComRelatorio -NoPause:$NoPause -Corpo {
    $repo = Get-RepoRaiz
    $alvo = Join-Path $repo "run_widget.pyw"
    if (-not (Test-Path $alvo)) {
        throw "run_widget.pyw nao encontrado em $repo"
    }

    $versao = Get-VersaoRepo
    $instalada = Get-VersaoInstalada
    $situacao = Compare-Versao -Repo $versao -Instalada $instalada

    Write-Host ""
    switch ($situacao) {
        "nova" {
            Write-Host "Instalando o CC Widget $versao..." -ForegroundColor Cyan
        }
        "atualizacao" {
            Write-Host "Atualizando: $instalada  ->  $versao" -ForegroundColor Cyan
        }
        "downgrade" {
            Write-Host "A versao instalada ($instalada) e mais nova que a deste" -ForegroundColor Yellow
            Write-Host "diretorio ($versao). Instalando a deste diretorio." -ForegroundColor Yellow
        }
        default {
            Write-Host "Versao $versao ja instalada. Substituindo os atalhos." -ForegroundColor Cyan
        }
    }

    $pythonw = Get-Pythonw
    $atalhos = Get-Atalhos
    foreach ($a in $atalhos) {
        New-Atalho -Caminho $a.Caminho -Pythonw $pythonw -Alvo $alvo -Repo $repo
    }
    Set-VersaoInstalada -Versao $versao

    Write-Host ""
    Write-Host "Atalhos:" -ForegroundColor Green
    foreach ($a in $atalhos) {
        Write-Host ("  {0,-17} {1}" -f $a.Nome, $a.Caminho) -ForegroundColor DarkGray
    }
    Write-Host ""

    if ($NoLaunch) {
        Write-Host "Para abrir:  pythonw `"$alvo`"" -ForegroundColor DarkGray
        return
    }

    $rodando = Test-WidgetRodando
    if ($rodando -and $situacao -eq "reinstalacao") {
        Write-Host "O widget ja esta aberto." -ForegroundColor DarkGray
        return
    }
    if ($rodando) {
        # A copia aberta e da versao anterior: reiniciar evita a confusao de
        # ver na tela algo diferente do que acabou de ser instalado.
        [void](Stop-Widget)
        Start-Sleep -Milliseconds 400
        Write-Host "Reiniciando o widget na versao nova..." -ForegroundColor DarkGray
    }
    Start-Process $pythonw -ArgumentList "`"$alvo`"" -WorkingDirectory $repo
    Write-Host "Widget aberto." -ForegroundColor Green
}
