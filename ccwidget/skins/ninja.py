"""Ninja: capuz fechado, bandana esvoacando e faixa na cintura."""

from .base import corpo, sobrepor, volume


def fresta(linhas) -> None:
    """A fresta de pele que o capuz deixa na altura dos olhos."""
    corpo(linhas, (3,), range(3, 16), "b")


def bandana(linhas) -> None:
    """Bandana na testa, com as pontas caindo pela direita.

    As pontas passam do corpo, entao usam `sobrepor`: ali fora nao ha nada
    para pintar por cima.
    """
    corpo(linhas, (1,), range(2, 17), "a")
    sobrepor(linhas, (1,), (17, 18), "a")
    sobrepor(linhas, (2,), (18,), "a")


def faixa_cintura(linhas) -> None:
    """Faixa amarrada na cintura, no mesmo vermelho da bandana."""
    corpo(linhas, (9,), range(2, 17), "a")


def punhos(linhas) -> None:
    """Bracos enfaixados: um cinza mais claro nas pontas."""
    corpo(linhas, (6, 7), (0, 1, 17, 18), "l")


SKIN = {
    "nome": "Ninja",
    "resumo": "Capuz fechado, bandana esvoaçando e faixa na cintura.",
    "cores": {
        "#": "#2b2d36", "s": "#1e2028", "l": "#3c3f4b",
        "a": "#b03a2e",   # bandana e faixa
        "b": "#e5c39b",   # a pele na fresta do capuz
    },
    "detalhes": (volume, fresta, bandana, faixa_cintura, punhos),
}
