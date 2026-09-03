"""Cavaleiro: elmo com penacho, viseira em T e a cruz no peitoral."""

from .base import corpo, volume


def viseira(linhas) -> None:
    """Viseira em T: a fresta dos olhos e a fenda do nariz, com respiros."""
    corpo(linhas, (1,), range(3, 16), "l")
    corpo(linhas, (3,), range(3, 16), "a")
    corpo(linhas, (4, 5), (9,), "a")
    corpo(linhas, (5,), (7, 11), "a")


def peitoral(linhas) -> None:
    """Peitoral com a cruz do brasao e dois rebites."""
    corpo(linhas, (8,), (8, 9, 10), "b")
    corpo(linhas, (9,), (9,), "b")
    corpo(linhas, (8,), (4, 14), "a")


def ombreiras(linhas) -> None:
    """Ombreiras: chapa clara em cima, sombra embaixo."""
    corpo(linhas, (6,), (0, 1, 17, 18), "l")
    corpo(linhas, (7,), (0, 1, 17, 18), "s")


SKIN = {
    "nome": "Cavaleiro",
    "resumo": "Elmo com penacho, viseira em T e a cruz no peitoral.",
    "cores": {
        "#": "#9aa2ab", "s": "#6b737d", "l": "#ced5db",
        "a": "#343a42",   # frestas da viseira e rebites
        "b": "#b8332a",   # penacho e brasao
    },
    "topo": (
        ".........b.........",
        "........bbb........",
        "...#####bbb#####...",
    ),
    "detalhes": (volume, viseira, peitoral, ombreiras),
}
