# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento em [SemVer](https://semver.org/lang/pt-BR/).

## [0.5.0] — 2026-09-03

### Adicionado

- Aviso de versão nova. Uma vez por dia o widget lê a versão publicada no
  GitHub e, se for maior que a instalada, mostra uma faixa no painel
  (**↑ Versão x.y.z disponível**) e transforma o rodapé do menu em
  **CC Widget a.b.c › atualizar para x.y.z**. Clicar em qualquer um dos dois
  abre uma janelinha com o comando de atualização (`git pull` e o instalador) e
  um botão para copiá-lo. A resposta fica guardada em `~/.ccwidget/config.json`,
  então o aviso reaparece nas aberturas seguintes até você atualizar — e some
  sozinho quando a versão local alcança a publicada.
- Interruptor **Avisar de novas versões** no menu. Desligado, nenhuma
  requisição sai da máquina. A consulta é um GET de um arquivo de texto público
  (`ccwidget/__init__.py` no repositório), roda numa thread com 8 s de limite e
  qualquer falha — sem rede, proxy no caminho, GitHub fora — é engolida em
  silêncio.

### Corrigido

- `python -m ccwidget report` quebrava com `UnicodeEncodeError` em console
  cp1252: `█`, `░` e `─` não existem nessa página de código, e a saída morria na
  primeira linha. Agora o desenho se adapta ao que o console aceita (blocos em
  UTF-8, cp437 e cp850; `#`, `.` e `-` onde eles não cabem), e o resto do texto
  vai com `errors="replace"` para nunca derrubar o comando.

## [0.4.0] — 2026-09-03

### Removido

- O widget não sobe mais junto com o Windows. O instalador criava um atalho na
  pasta Inicializar, e subir no login — junto com todo o resto — deixava a
  máquina travada nos primeiros minutos. Agora só existe o atalho da área de
  trabalho: o widget abre quando você quiser. O instalador e o desinstalador
  apagam o atalho que ficou de versões anteriores.

### Adicionado

- Intervalos curtos em **⚙ › Atualizar a cada**: 30 segundos, 1, 2 e 5 minutos,
  ao lado dos que já existiam. Cada consulta inicia o CLI do Claude Code, então
  os intervalos curtos cobram alguns segundos de CPU de cada vez.
- O desinstalador pergunta no terminal o que fazer com as preferências —
  manter, apagar `~/.ccwidget` junto, ou cancelar sem mexer em nada — em vez de
  exigir o parâmetro `-Tudo` de quem abre o script com um duplo clique. Os
  parâmetros continuam valendo (`-Tudo`, e agora `-Manter`) e dispensam a
  pergunta; sem console para perguntar, as preferências ficam.

### Alterado

- A primeira consulta ao `/usage` acontece ao abrir a janela, sem esperar
  clique no botão de atualizar. Vale mesmo com o intervalo em **Só manual**;
  reabrir logo depois de fechar não consulta de novo, porque o dado em disco
  ainda serve.

### Corrigido

- Durações abaixo de um minuto aparecem em segundos (`40 s`) no lugar de
  `0 min` — visível na conta até a próxima consulta com o intervalo em 30
  segundos.
- Escolher um intervalo no menu **Atualizar a cada** passou a reagendar o laço
  de consultas. Antes só o relógio do rodapé mudava: o laço seguia na cadência
  anterior e, vindo de **Só manual**, não havia laço nenhum para reagendar — a
  contagem chegava a zero e nada acontecia.

## [0.3.0] — 2026-09-02

### Adicionado

- Animação de entrada e de saída: ao abrir, o mascote cumprimenta no meio da
  janela e sobe para o cabeçalho enquanto o painel é revelado de baixo para
  cima; ao fechar, faz o caminho inverso, se despede e sai de cena.
- Dezesseis gracinhas no modo minimizado, sorteadas a cada 25–70 segundos:
  piscar, acenar, pisar no lugar, olhar para os lados, espiar, piscadela,
  espreguiçar, pular, dançar, se sacudir, cochilar, ficar com sono, se
  surpreender, sorrir (`> <`), pôr óculos e pôr óculos escuros.
- Dez aparências para o mascote em **⚙ › Mascote**: clássico, monstro, robô,
  alienígena, ninja, esqueleto, mago, pirata, raposa e cavaleiro. Cada uma
  define cores próprias, detalhes no corpo e acessórios desenhados acima dele.
- Interruptor **Animações** no menu: desligado, o widget abre e fecha na hora e
  o mascote para de se mexer. A preferência persiste.

### Alterado

- A arte do mascote foi revista a partir das referências oficiais: olhos
  verticais de três blocos e quatro perninhas separadas, no lugar dos olhos
  achatados e pés finos extraídos do terminal.

## [0.2.1] — 2026-09-02

### Corrigido

- O controle de opacidade percorria a faixa inteira de alfa, e nas posições
  baixas o widget se dissolvia no fundo — sem forma de enxergar o que ajustar.
  A escala continua de 1 a 100 para quem usa, mas agora percorre de 40% a 100%
  de opacidade real, onde o conteúdo permanece legível. Configurações gravadas
  abaixo desse piso são normalizadas ao abrir.

## [0.2.0] — 2026-09-02

### Adicionado

- Cópia única: clicar no atalho com o widget já aberto não abre uma segunda
  janela. A cópia em execução vem para frente, e volta para a tela principal se
  estava numa posição que deixou de existir (monitor desconectado).
- Controle de opacidade contínuo, de 1% a 100%, no lugar dos quatro valores
  fixos. A janelinha do controle fica sempre opaca, para ser possível desfazer
  um ajuste que tenha deixado o widget quase invisível.

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
