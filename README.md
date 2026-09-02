<div align="center">

<img src="docs/mascote.png" width="114" alt="">

# CC Widget

**Seus limites do Claude Code na área de trabalho: sessão de 5 horas e limite semanal, sempre acima das outras janelas.**

<img src="docs/painel-escuro.png" width="270" alt="Painel do widget">

Windows · Python 3.10+ · sem dependências · não-oficial

</div>

---

## Requisitos

- Windows com Python 3.10 ou mais novo
- CLI do Claude Code no `PATH` (o widget o executa)
- Nenhum pacote a instalar: só a biblioteca padrão

## Instalação

```powershell
git clone https://github.com/Luis-lhgdf/claudecode-usage-widget.git
cd claudecode-usage-widget

pythonw run_widget.pyw           # abre o widget
.\scripts\install-startup.ps1    # opcional: abre junto com o Windows
```

| Arquivo | Para que serve |
|---|---|
| `run_widget.pyw` | **Abre o widget.** É o que você executa para usar. A extensão `.pyw` faz o Windows usar `pythonw.exe`, sem janela de console |
| `scripts/install-startup.ps1` | **Roda uma única vez.** Cria um atalho para o `run_widget.pyw` na pasta Inicializar, para o widget subir sozinho no login. `-Remove` desfaz |

## Modos

<table>
<tr>
<td align="center" width="35%"><img src="docs/minimizado.png" width="88" alt="Minimizado"><br><b>Minimizado</b><br><sub>Percentual e tempo até o reset</sub></td>
<td align="center" width="65%"><img src="docs/painel-escuro.png" width="230" alt="Painel"><br><b>Painel</b><br><sub>Sessão atual e semana</sub></td>
</tr>
</table>

## Controles

| Ação | Resultado |
|---|---|
| `↻` | Consulta o `/usage` agora |
| `⚙` ou botão direito | Menu: modo, tema, intervalo, opacidade |
| `─` | Minimiza para o círculo |
| `✕` ou `Esc` | Fecha |
| Arrastar cabeçalho ou círculo | Move |
| Clicar no círculo | Abre o painel |

## De onde vêm os números

Uma fonte só, a oficial: o widget roda `claude -p "/usage"` e interpreta a saída. É comando local, sem resposta de modelo — **não consome tokens**. Roda a cada 10 minutos (ajustável no menu) e sob demanda no `↻`.

Durante a consulta a seta gira e as barras viram um segmento correndo na pista. Sem dado, o widget mostra `--` e diz que não tem dado — ele não estima consumo por conta própria.

<div align="center">
<img src="docs/carregando.png" width="270" alt="Durante a consulta">
</div>

## Tema

Claro e escuro, seguindo o Windows por padrão. Fixe um dos dois no menu.

<div align="center">
<img src="docs/painel-claro.png" width="270" alt="Tema claro">
</div>

## Terminal

```bash
python -m ccwidget usage     # consulta e grava
python -m ccwidget report    # imprime os percentuais
```

## Configuração

Tudo em `~/.ccwidget/config.json`: modo, tema, posição, opacidade e `usage_refresh_minutes` (`0` desliga a consulta automática). O menu cobre todos eles.

## Estrutura

```
ccwidget/
  usage_cli.py   roda o `claude -p /usage` e interpreta a saída
  state.py       lê e grava o último resultado
  theme.py       paletas, mascote e formas com antialiasing
  ui.py          o widget tkinter
  config.py      preferências
  __main__.py    entrada (widget / usage / report)
run_widget.pyw   abre sem console
scripts/         instalador de inicialização
```

## Desinstalar

```powershell
.\scripts\install-startup.ps1 -Remove
```

Depois remova `~/.ccwidget/`.

---

## English

Floating desktop widget for Claude Code limits — 5-hour session window and weekly limit, always on top, minimized ring or full panel, light and dark themes.

Numbers come from one official source: the widget runs `claude -p "/usage"` and parses its output. Local command, no model response, no tokens spent; every 10 minutes (configurable) and on demand. It never estimates usage on its own — with no data, it says so.

Requires the Claude Code CLI on `PATH` and Python 3.10+. No packages to install. **Interface is in Portuguese.**

```powershell
pythonw run_widget.pyw
python -m ccwidget report
```

---

## Licença

MIT — veja [LICENSE](LICENSE).

Sem vínculo com a Anthropic. "Claude" é marca da Anthropic, PBC; o mascote é desenhado em código (`ccwidget/theme.py`), nenhum arquivo de marca acompanha o repositório. O projeto apenas executa um comando público do CLI e lê o resultado.
