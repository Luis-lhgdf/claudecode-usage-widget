"""Pirata: chapeu com caveira, tapa-olho, brinco e camisa listrada."""

from .base import corpo, sobrepor, volume


def tapa_olho(linhas) -> None:
    """Tapa-olho cobrindo o olho esquerdo.

    Sem correia de proposito: a aba do chapeu ja passa rente a testa, e um
    segundo risco escuro ali deixava o rosto inteiro em sombra.
    """
    sobrepor(linhas, (2, 3, 4), (3, 4, 5, 6), "a")


def dente_de_ouro(linhas) -> None:
    """Sorriso torto com um dente de ouro no meio."""
    corpo(linhas, (5,), range(7, 12), "a")
    sobrepor(linhas, (5,), (9,), "c")


def listras(linhas) -> None:
    """Camisa listrada por baixo do casaco."""
    corpo(linhas, (7,), range(0, 19), "b")
    corpo(linhas, (9,), range(2, 17), "b")


def brinco(linhas) -> None:
    """Argola dourada na orelha direita."""
    corpo(linhas, (5,), (16,), "c")


SKIN = {
    "nome": "Pirata",
    "resumo": "Chapéu com caveira, tapa-olho, brinco e camisa listrada.",
    "cores": {
        "#": "#c85a45", "s": "#a44634", "l": "#dd7259",
        "a": "#22242c",   # chapeu e tapa-olho
        "b": "#efe9dc",   # caveira do chapeu e listras
        "c": "#e8b53d",   # brinco e dente de ouro
    },
    # A aba passa da largura da cabeca: e o que faz o chapeu parecer chapeu em
    # vez de uma faixa preta no alto do corpo.
    "topo": (
        "...a...........a...",
        "...aaaaabbbaaaaa...",
        ".aaaaaaababaaaaaaa.",
    ),
    "detalhes": (volume, tapa_olho, dente_de_ouro, listras, brinco),
}
