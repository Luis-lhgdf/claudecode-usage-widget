"""Ferramentas comuns a todas as skins.

Uma skin veste o mascote: troca as cores, pinta tracos dentro do corpo e pode
acrescentar um "topo" -- chapeu, orelhas, antenas -- desenhado acima dele.

O corpo continua sendo o MASCOT de 19x12 do `theme`, e e nele que as poses
mexem. O topo entra so na hora de desenhar, entao acessorio nenhum atrapalha
as animacoes.

Na arte, cada caractere e uma cor: "#" e a cor principal, "s" e "l" sao a
sombra e a luz do proprio corpo e "a".."d" sao cores livres que cada skin
declara. "." e vazio.
"""

from __future__ import annotations

# O topo cabe em ate tres linhas. Mais que isso e a arte encosta na borda do
# disco do modo mini, onde o mascote ja fica perto do alto do circulo.
TOPO_MAX = 3

# Caracteres que contam como corpo. Um detalhe pinta por cima deles, mas nunca
# por cima de um vao -- os vaos sao o que as poses desenham, e apagar um deles
# fecharia os olhos do mascote no meio de uma gracinha.
CORPO_CHARS = "#sl"


def corpo(linhas, ys, xs, cor: str) -> None:
    """Pinta as celulas de corpo indicadas, deixando os vaos intactos."""
    for y in ys:
        if not 0 <= y < len(linhas):
            continue
        for x in xs:
            if 0 <= x < len(linhas[y]) and linhas[y][x] in CORPO_CHARS:
                linhas[y][x] = cor


def sobrepor(linhas, ys, xs, cor: str) -> None:
    """Pinta por cima de tudo, inclusive dos vaos.

    E o que um tapa-olho, uma presa ou a ponta de uma faixa precisam: eles
    cobrem o desenho em vez de acompanhar o corpo.
    """
    for y in ys:
        if not 0 <= y < len(linhas):
            continue
        for x in xs:
            if 0 <= x < len(linhas[y]):
                linhas[y][x] = cor


def volume(linhas) -> None:
    """Uma luz em cima e uma sombra embaixo, para o corpo nao ser chapado.

    E o unico detalhe que todas as skins usam, e vem sempre primeiro: sem ele
    o mascote e uma mancha de cor so, e qualquer traco pintado depois flutua
    sem apoio.
    """
    corpo(linhas, (0,), range(2, 17), "l")        # alto da cabeca
    corpo(linhas, (9,), range(2, 17), "s")        # base do tronco
    corpo(linhas, (7,), (0, 1, 17, 18), "s")      # baixo dos bracos
    corpo(linhas, (11,), range(0, 19), "s")       # pes
