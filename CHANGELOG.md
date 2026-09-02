# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento em [SemVer](https://semver.org/lang/pt-BR/).

## [0.1.1] — 2026-09-02

### Corrigido

- O valor padrão de `mode` ainda era `"summary"`, nome de um modo que deixou de
  existir quando os modos foram reduzidos a `mini` e `panel`. Numa instalação
  nova o widget caía no fallback e funcionava, mas gravava um modo inválido na
  configuração. Encontrado ao rodar o instalador do zero.

## [0.1.0] — 2026-09-02

Primeira versão pública.

### Adicionado

- Widget flutuante com a sessão de 5 horas e o limite semanal do Claude Code,
  sempre acima das outras janelas e arrastável.
- Dois modos: círculo minimizado (percentual e tempo até o reset) e painel.
- Temas claro e escuro, seguindo a preferência do Windows por padrão.
- Consulta automática ao `claude -p "/usage"` a cada 10 minutos, com intervalo
  ajustável no menu (5, 10, 15, 30, 60 minutos ou só manual) e busca sob
  demanda no botão de atualizar.
- Sinalização de carregamento durante a consulta: seta girando, barras
  indeterminadas e o mascote caminhando.
- Mascote do Claude Code em pixel art e formas curvas rasterizadas com
  antialiasing próprio, sem dependências externas.
- `python -m ccwidget report` e `python -m ccwidget usage` para uso no terminal.
- Instalador (`scripts/install.ps1`): cria atalhos com o ícone do mascote na
  pasta Inicializar e na área de trabalho, registra a versão instalada e abre o
  widget. Rodar de novo compara a versão do repositório com a registrada e
  identifica instalação, atualização, reinstalação ou downgrade.
- Desinstalador (`scripts/uninstall.ps1`), com `-Tudo` para apagar também as
  preferências.
- Versão do pacote em `ccwidget.__version__`, exibida no rodapé do menu.

### Notas

- Os percentuais vêm apenas da fonte oficial. Sem dado, o widget informa a
  ausência em vez de estimar consumo.
- Requer o CLI do Claude Code no `PATH` e Python 3.10 ou mais novo.
