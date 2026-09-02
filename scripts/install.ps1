<#
.SYNOPSIS
    Instala os atalhos do CC Widget.

.DESCRIPTION
    Cria dois atalhos para run_widget.pyw: um na pasta Inicializar, para o
    widget subir junto com o Windows, e outro na area de trabalho, para abrir
    quando voce quiser. Ambos usam pythonw.exe, entao nenhuma janela de console
    aparece.

    Rode uma vez. Nao e este script que abre o widget -- para abrir agora, use
    run_widget.pyw.

.PARAMETER Remove
    Remove os atalhos em vez de criar.

.PARAMETER NoPause
    Nao espera Enter no fim. Util ao chamar de outro script.

.EXAMPLE
    .\scripts\install.ps1
    .\scripts\install.ps1 -Remove
#>
[CmdletBinding()]
param([switch]$Remove, [switch]$NoPause)

$ErrorActionPreference = "Stop"


function Test-JanelaPropria {
    <#
        A janela deve esperar Enter apenas quando foi aberta so para rodar este
        script -- caso de "Executar com PowerShell" no Explorer --, porque ela
        fecha junto com ele e leva a mensagem embora. Chamado de um terminal
        que ja estava aberto, pausar so atrapalharia.
    #>
    if ($NoPause) { return $false }
    try {
        $paiId = (Get-CimInstance Win32_Process -Filter "ProcessId=$PID").ParentProcessId
        $pai = (Get-Process -Id $paiId -ErrorAction Stop).ProcessName
        return $pai -in @("explorer", "svchost", "dllhost")
    } catch {
        return $false
    }
}


function Get-Atalhos {
    @(
        @{ Nome = "Inicializar";      Caminho = Join-Path ([Environment]::GetFolderPath("Startup")) "CC Widget.lnk" }
        @{ Nome = "Area de Trabalho"; Caminho = Join-Path ([Environment]::GetFolderPath("Desktop")) "CC Widget.lnk" }
    )
}


function New-Atalho {
    param($Caminho, $Pythonw, $Alvo, $Repo)

    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($Caminho)
    $link.TargetPath = $Pythonw
    $link.Arguments = "`"$Alvo`""
    $link.WorkingDirectory = $Repo
    $link.Description = "CC Widget - uso do Claude Code"
    $link.Save()
}


function Invoke-Instalacao {
    $atalhos = Get-Atalhos

    if ($Remove) {
        $removidos = 0
        foreach ($a in $atalhos) {
            if (Test-Path $a.Caminho) {
                Remove-Item $a.Caminho -Force
                Write-Host "Removido de $($a.Nome)." -ForegroundColor Green
                $removidos++
            }
        }
        if (-not $removidos) {
            Write-Host "Nenhum atalho encontrado." -ForegroundColor DarkGray
        }
        return
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
        if (-not $python) {
            throw "Python nao encontrado no PATH. Instale o Python 3.10+ e tente de novo."
        }
        $pythonw = Join-Path (Split-Path $python) "pythonw.exe"
        if (-not (Test-Path $pythonw)) {
            throw "pythonw.exe nao encontrado ao lado de $python"
        }
    }

    foreach ($a in $atalhos) {
        New-Atalho -Caminho $a.Caminho -Pythonw $pythonw -Alvo $target -Repo $repo
    }

    Write-Host ""
    Write-Host "Pronto. Dois atalhos criados:" -ForegroundColor Green
    Write-Host ""
    foreach ($a in $atalhos) {
        Write-Host ("  {0,-17} {1}" -f $a.Nome, $a.Caminho) -ForegroundColor DarkGray
    }
    Write-Host ""
    Write-Host "O widget abre junto com o Windows, e o atalho da area de" -ForegroundColor Cyan
    Write-Host "trabalho abre quando voce quiser." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Para abrir agora, sem reiniciar:"
    Write-Host "  pythonw `"$target`"" -ForegroundColor DarkGray
}


$falhou = $false
try {
    Invoke-Instalacao
} catch {
    # Sem este catch a janela fecharia no throw, antes de mostrar o motivo.
    Write-Host ""
    Write-Host "FALHOU: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    $falhou = $true
} finally {
    if (Test-JanelaPropria) {
        Write-Host ""
        Read-Host "Pressione Enter para fechar"
    }
}

if ($falhou) { exit 1 }
