<div align="center">

<img src="docs/mascote.png" width="114" alt="">

# CC Widget

**Seus limites do Claude Code na área de trabalho: sessão de 5 horas e limite semanal, sempre acima das outras janelas.**

<img src="docs/painel-escuro.png" width="270" alt="Painel do widget">

![Versão](https://img.shields.io/badge/vers%C3%A3o-0.3.0-d97757)
![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-4d7a3a)
![Python](https://img.shields.io/badge/python-3.10%2B-d97757)
![Plataforma](https://img.shields.io/badge/plataforma-Windows-6d6659)
![Dependências](https://img.shields.io/badge/depend%C3%AAncias-nenhuma-4d7a3a)

Projeto não-oficial

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

.\scripts\install.ps1
```

O instalador cria os atalhos, registra a versão e abre o widget. Clicar no atalho de novo não abre uma segunda cópia — traz a que já está aberta para frente.

| Arquivo | Para que serve |
|---|---|
| `scripts/install.ps1` | **Instala.** Cria dois atalhos com o ícone do mascote — um na pasta Inicializar, para subir com o Windows, outro na área de trabalho — e abre o widget. Rodar de novo é seguro: compara a versão do repositório com a registrada e diz se é instalação, atualização ou reinstalação |
| `scripts/uninstall.ps1` | **Desinstala.** Fecha o widget e remove os atalhos. As preferências ficam; `-Tudo` apaga `~/.ccwidget` também |
| `run_widget.pyw` | **Abre o widget** sem passar pelo instalador. A extensão `.pyw` faz o Windows usar `pythonw.exe`, sem janela de console |

Para atualizar, basta `git pull` e rodar o instalador de novo — ele reinicia o widget na versão nova.

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
| `⚙` ou botão direito | Menu: modo, tema, mascote, intervalo, opacidade, animações |
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

## Mascote

Dez aparências em **⚙ › Mascote**. Cada uma tem cores próprias, detalhes no
corpo e acessórios — chapéu, antenas, orelhas — desenhados acima dele.

<div align="center">
<img src="docs/skins.png" width="640" alt="As dez aparências do mascote">
</div>

## Animações

Ao abrir, o mascote cumprimenta e sobe para o cabeçalho enquanto o painel
aparece; ao fechar, desce, se despede e sai de cena. No modo minimizado ele faz
uma de dezesseis gracinhas a cada 25–70 segundos.

<div align="center">
<img src="docs/gracinhas.png" width="420" alt="As gracinhas do mascote">
</div>

Tudo isso se desliga em **⚙ › Animações** — aí o widget abre e fecha na hora.

## Terminal

```bash
python -m ccwidget usage     # consulta e grava
python -m ccwidget report    # imprime os percentuais
```

## Configuração

Tudo em `~/.ccwidget/config.json`: modo, tema, posição, opacidade, `usage_refresh_minutes` (`0` desliga a consulta automática) e a versão instalada. O menu cobre as preferências; a versão quem escreve é o instalador.

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
scripts/         install.ps1, uninstall.ps1 e as funções comuns
assets/          ícone do mascote (.ico)
```

## Desinstalar

```powershell
.\scripts\uninstall.ps1          # remove os atalhos, mantém as preferências
.\scripts\uninstall.ps1 -Tudo    # remove também ~/.ccwidget
```

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

MIT — veja [LICENSE](LICENSE). Histórico em [CHANGELOG.md](CHANGELOG.md).

Sem vínculo com a Anthropic. "Claude" é marca da Anthropic, PBC; o mascote é desenhado em código (`ccwidget/theme.py`), nenhum arquivo de marca acompanha o repositório. O projeto apenas executa um comando público do CLI e lê o resultado.
