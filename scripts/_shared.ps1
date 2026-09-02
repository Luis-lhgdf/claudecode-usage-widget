<#
    Funcoes usadas por install.ps1 e uninstall.ps1.

    Nao rode este arquivo direto: ele so define funcoes, carregadas pelos
    outros scripts com dot-sourcing.
#>

function Get-Atalhos {
    <# Os dois lugares onde o atalho do widget e criado. #>
    @(
        @{ Nome = "Inicializar";      Caminho = Join-Path ([Environment]::GetFolderPath("Startup")) "CC Widget.lnk" }
        @{ Nome = "Area de Trabalho"; Caminho = Join-Path ([Environment]::GetFolderPath("Desktop")) "CC Widget.lnk" }
    )
}


function Get-RepoRaiz {
    Split-Path -Parent $PSScriptRoot
}


function Get-Pythonw {
    <# pythonw roda sem console; com python.exe um terminal preto ficaria aberto. #>
    $pythonw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
    if ($pythonw) { return $pythonw }

    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) {
        throw "Python nao encontrado no PATH. Instale o Python 3.10+ e tente de novo."
    }
    $pythonw = Join-Path (Split-Path $python) "pythonw.exe"
    if (-not (Test-Path $pythonw)) {
        throw "pythonw.exe nao encontrado ao lado de $python"
    }
    return $pythonw
}


function New-Atalho {
    param($Caminho, $Pythonw, $Alvo, $Repo)

    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($Caminho)
    $link.TargetPath = $Pythonw
    $link.Arguments = "`"$Alvo`""
    $link.WorkingDirectory = $Repo
    $link.Description = "CC Widget - uso do Claude Code"

    # Sem isto o atalho herda o icone do pythonw.exe, e na area de trabalho
    # aparece o logo do Python em vez do mascote.
    $icone = Join-Path $Repo "assets\cc-widget.ico"
    if (Test-Path $icone) {
        $link.IconLocation = "$icone,0"
    }
    $link.Save()
}


function Test-WidgetRodando {
    <#
        Procura um pythonw executando run_widget.pyw, para nao abrir uma
        segunda copia por cima da que ja esta na tela.
    #>
    try {
        $achou = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" -ErrorAction Stop |
            Where-Object { $_.CommandLine -like "*run_widget.pyw*" }
        return [bool]$achou
    } catch {
        return $false
    }
}


function Stop-Widget {
    <# Encerra as copias abertas do widget. #>
    try {
        $procs = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" -ErrorAction Stop |
            Where-Object { $_.CommandLine -like "*run_widget.pyw*" }
        foreach ($p in $procs) {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        }
        return @($procs).Count
    } catch {
        return 0
    }
}


function Test-JanelaPropria {
    <#
        A janela deve esperar Enter apenas quando foi aberta so para rodar o
        script -- caso de "Executar com PowerShell" no Explorer --, porque ela
        fecha junto e leva a mensagem embora. Chamado de um terminal que ja
        estava aberto, pausar so atrapalharia.
    #>
    param([switch]$NoPause)

    if ($NoPause) { return $false }
    try {
        $paiId = (Get-CimInstance Win32_Process -Filter "ProcessId=$PID").ParentProcessId
        $pai = (Get-Process -Id $paiId -ErrorAction Stop).ProcessName
        return $pai -in @("explorer", "svchost", "dllhost")
    } catch {
        return $false
    }
}


function Invoke-ComRelatorio {
    <#
        Roda o bloco mostrando a falha em vez de sumir com a janela, e espera
        Enter quando o console foi aberto so para isto.
    #>
    param([scriptblock]$Corpo, [switch]$NoPause)

    $falhou = $false
    try {
        & $Corpo
    } catch {
        Write-Host ""
        Write-Host "FALHOU: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        $falhou = $true
    } finally {
        if (Test-JanelaPropria -NoPause:$NoPause) {
            Write-Host ""
            Read-Host "Pressione Enter para fechar"
        }
    }
    if ($falhou) { exit 1 }
}


function Get-VersaoRepo {
    <# Le a versao direto do pacote: o codigo e a fonte da verdade. #>
    $init = Join-Path (Get-RepoRaiz) "ccwidget\__init__.py"
    if (-not (Test-Path $init)) { return $null }
    $texto = Get-Content $init -Raw
    if ($texto -match '__version__\s*=\s*"([^"]+)"') { return $Matches[1] }
    return $null
}


function Get-ConfigPath {
    Join-Path $HOME ".ccwidget\config.json"
}


function Get-VersaoInstalada {
    <# Versao registrada na ultima instalacao, ou $null se nunca instalou. #>
    $cfg = Get-ConfigPath
    if (-not (Test-Path $cfg)) { return $null }
    try {
        $dados = Get-Content $cfg -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($dados.PSObject.Properties.Name -contains "installed_version") {
            return $dados.installed_version
        }
    } catch {
        return $null
    }
    return $null
}


function Set-VersaoInstalada {
    param([string]$Versao)

    $cfg = Get-ConfigPath
    $dados = @{}
    if (Test-Path $cfg) {
        try {
            $lido = Get-Content $cfg -Raw -Encoding UTF8 | ConvertFrom-Json
            foreach ($p in $lido.PSObject.Properties) { $dados[$p.Name] = $p.Value }
        } catch {
            $dados = @{}
        }
    }
    $dados["installed_version"] = $Versao

    New-Item -ItemType Directory -Force (Split-Path $cfg) | Out-Null
    # WriteAllText nao poe BOM; Set-Content poria, e o widget teria de contornar.
    [System.IO.File]::WriteAllText($cfg, ($dados | ConvertTo-Json -Depth 5), [System.Text.UTF8Encoding]::new($false))
}


function Compare-Versao {
    <#
        Compara a versao do repositorio com a instalada e devolve o que fazer:
        "nova", "atualizacao", "reinstalacao" ou "downgrade".
    #>
    param([string]$Repo, [string]$Instalada)

    if (-not $Instalada) { return "nova" }
    try {
        $a = [version]$Repo
        $b = [version]$Instalada
    } catch {
        return "reinstalacao"
    }
    if ($a -gt $b) { return "atualizacao" }
    if ($a -lt $b) { return "downgrade" }
    return "reinstalacao"
}
