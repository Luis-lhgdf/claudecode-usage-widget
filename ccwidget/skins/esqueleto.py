"""Esqueleto: orbitas fundas, dentes a mostra e a caixa toracica aberta."""

from .base import corpo, sobrepor, volume


def cranio(linhas) -> None:
    """Orbitas fundas e a cavidade nasal."""
    corpo(linhas, (1,), (4, 5, 13, 14), "a")
    corpo(linhas, (2, 3, 4), (3, 6, 12, 15), "a")
    corpo(linhas, (3,), (9,), "a")
    corpo(linhas, (4,), (8, 9, 10), "a")


def dentes(linhas) -> None:
    """Fileira de dentes: o vao escuro da boca com o osso entre eles."""
    corpo(linhas, (5,), range(4, 15), "a")
    sobrepor(linhas, (5,), (5, 7, 9, 11, 13), "l")


def costelas(linhas) -> None:
    """Caixa toracica: quatro vaos escuros e o esterno no meio."""
    corpo(linhas, (8, 9), (5, 7, 11, 13), "a")
    corpo(linhas, (8, 9), (9,), "s")


SKIN = {
    "nome": "Esqueleto",
    "resumo": "Órbitas fundas, dentes à mostra e a caixa torácica aberta.",
    "cores": {
        "#": "#eae6d8", "s": "#c2bba7", "l": "#f7f4ea",
        "a": "#403d36",   # as cavidades
    },
    "detalhes": (volume, cranio, dentes, costelas),
}
