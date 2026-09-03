"""Monstro: chifres de osso, testa pesada e uma bocarra de presas."""

from .base import corpo, sobrepor, volume


def sobrancelha(linhas) -> None:
    """Testa pesada: uma faixa de sombra logo acima dos olhos."""
    corpo(linhas, (1,), range(3, 16), "s")


def espinhos(linhas) -> None:
    """Pontas de osso saindo das laterais, no mesmo tom dos chifres."""
    corpo(linhas, (1, 4, 8), (2, 16), "a")


def barriga(linhas) -> None:
    """Barriga clara: separa o tronco da massa escura do resto."""
    corpo(linhas, (8, 9), range(6, 13), "l")


def bocarra(linhas) -> None:
    """Bocarra escura, rasgada de ponta a ponta, com tres presas.

    As presas usam `sobrepor` porque a boca ja deixou de ser corpo: pintadas
    com `corpo` elas simplesmente nao apareceriam.
    """
    corpo(linhas, (5,), range(4, 15), "b")
    sobrepor(linhas, (5,), (6, 9, 12), "a")


def garras(linhas) -> None:
    """Uma garra clara na ponta de cada pe."""
    corpo(linhas, (11,), (2, 7, 11, 16), "a")


SKIN = {
    "nome": "Monstro",
    "resumo": "Chifres de osso, bocarra com presas e garras nos pés.",
    "cores": {
        "#": "#7ba24f", "s": "#5c7c39", "l": "#a2c46c",
        "a": "#efe6cf",   # osso: chifres, espinhos, presas e garras
        "b": "#3d1f2b",   # o vao da boca
    },
    "topo": (
        "..a.............a..",
        "..aa...........aa..",
    ),
    "detalhes": (volume, sobrancelha, espinhos, barriga, bocarra, garras),
}
