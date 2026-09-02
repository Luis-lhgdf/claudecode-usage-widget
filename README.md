<div align="center">

# Claude Code Usage Widget

**Widget flutuante que mostra seus limites do Claude Code na área de trabalho: sessão de 5 horas e limite semanal, sempre acima das outras janelas.**

<img src="docs/painel-escuro.png" width="270" alt="Painel do widget no tema escuro">

Windows · Python 3.10+ · sem dependências · projeto não-oficial

</div>

---

## Por quê

Celular tem widget para tudo. Computador, quase nada. E o número que importa enquanto você trabalha — *quanto já foi da minha janela de 5 horas?* — fica atrás do `/usage`, que você precisa parar e digitar.

Isso põe o número na tela, permanentemente.

## Dois modos

Alterne pelo botão `⋮`, por duplo clique no cabeçalho, ou clicando no círculo.

<table>
<tr>
<td align="center" width="40%"><img src="docs/minimizado.png" width="64" alt="Modo minimizado"><br><b>Minimizado</b><br><sub>Círculo flutuante com o mascote<br>e o anel da sessão</sub></td>
<td align="center" width="60%"><img src="docs/painel-escuro.png" width="230" alt="Painel"><br><b>Painel</b><br><sub>Sessão atual e limite semanal</sub></td>
</tr>
</table>

## Tema claro e escuro

Segue o Windows por padrão, ou fixe um dos dois pelo menu.

<div align="center">
<img src="docs/painel-claro.png" width="270" alt="Painel no tema claro">
</div>

## De onde vêm os números

De uma única fonte, a oficial:

```bash
claude -p "/usage"
```

O widget roda esse comando, interpreta a saída (percentuais, horários de reset e fuso) e guarda o resultado em `~/.ccwidget/state.json`. É um comando local — não há resposta de modelo, então **não consome tokens**. Como leva alguns segundos para o CLI iniciar, a consulta acontece em intervalo configurável (10 minutos por padrão) e sob demanda pelo menu, nunca no laço da interface.

**O widget não estima consumo por conta própria.** Se ainda não houve consulta, ele mostra `--` e diz isso, em vez de exibir um número inventado.

O selo no cabeçalho indica o estado:

| Selo | Significado |
|---|---|
| `oficial` | Consulta recente — os mesmos números do `/usage` |
| `antigo` | Passou mais de 20 minutos desde a última consulta |
| `sem dado` | Nenhuma consulta ainda |

## Instalação

```powershell
git clone https://github.com/Luis-lhgdf/claudecode-usage-widget.git
cd claudecode-usage-widget

pythonw run_widget.pyw              # abre o widget

.\scripts\install-startup.ps1       # opcional: abre junto com o Windows
```

Requer o CLI do Claude Code no `PATH` (o widget o executa) e Python 3.10 ou mais novo. Nenhum pacote para instalar: só a biblioteca padrão.

## Uso

| Ação | Resultado |
|---|---|
| Arrastar o cabeçalho ou o círculo | Move o widget |
| Clicar no círculo | Abre o painel |
| Duplo clique no cabeçalho | Minimiza |
| `–` | Minimiza para o círculo |
| `⋮` ou botão direito | Menu: modo, tema, atualizar, opacidade |
| `✕` ou `Esc` | Fecha |

Sem janela, direto no terminal:

```bash
python -m ccwidget usage     # consulta e grava
python -m ccwidget report    # imprime os percentuais
```

Modo, tema, posição e opacidade ficam em `~/.ccwidget/config.json` — inclusive `usage_refresh_minutes`, que controla o intervalo entre consultas (`0` desliga a consulta automática).

## Estrutura

```
ccwidget/
  usage_cli.py   roda o `claude -p /usage` e interpreta a saída
  state.py       lê e escreve o último resultado conhecido
  theme.py       paletas clara/escura e o mascote em pixel art
  ui.py          o widget tkinter
  config.py      preferências persistentes
  __main__.py    entrada (widget / usage / report)
run_widget.pyw   abre sem janela de console
scripts/         instalador de inicialização automática
```

## Desinstalar

```powershell
.\scripts\install-startup.ps1 -Remove
```

Depois remova a pasta `~/.ccwidget/`.

---

## English

A floating desktop widget for Claude Code limits: the 5-hour session window and the weekly limit, always on top, as a minimized ring or a full panel, with light and dark themes.

Numbers come from a single official source — the widget runs `claude -p "/usage"` and parses its output. That's a local command with no model response, so it costs no tokens; it runs on a configurable interval (10 minutes by default) and on demand from the menu. The widget never estimates consumption on its own: with no data yet, it says so instead of showing an invented figure.

Requires the Claude Code CLI on `PATH` and Python 3.10+. No packages to install — standard library only. **The interface is in Portuguese.**

```powershell
pythonw run_widget.pyw          # run
python -m ccwidget report       # terminal output
```

---

## Licença

MIT — veja [LICENSE](LICENSE).

Sem vínculo com a Anthropic. "Claude" é marca da Anthropic, PBC, e o mascote exibido é desenhado em código (`ccwidget/theme.py`) — nenhum arquivo de marca acompanha o repositório. Este projeto apenas executa um comando público do CLI e lê o próprio resultado; não modifica o Claude Code nem chama qualquer API privada.
