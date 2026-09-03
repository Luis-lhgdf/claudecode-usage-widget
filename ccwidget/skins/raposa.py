"""Raposa: orelhas de ponta, focinho branco e patas escuras."""

from .base import corpo, volume


def focinho(linhas) -> None:
    """Focinho claro, nariz escuro e as bochechas de pelo branco."""
    corpo(linhas, (3, 4), (2, 3, 15, 16), "a")
    corpo(linhas, (5,), range(5, 14), "a")
    corpo(linhas, (4,), (8, 9, 10), "b")


def peito(linhas) -> None:
    """Peito branco descendo pelo tronco."""
    corpo(linhas, (8, 9), range(6, 13), "a")


def patas(linhas) -> None:
    """Patas escuras, as meias da raposa."""
    corpo(linhas, (10, 11), range(0, 19), "b")
    corpo(linhas, (7,), (0, 1, 17, 18), "b")


SKIN = {
    "nome": "Raposa",
    "resumo": "Orelhas de ponta, focinho branco, nariz escuro e patas pretas.",
    "cores": {
        "#": "#e07b39", "s": "#bd6127", "l": "#f0954f",
        "a": "#f8eedb",   # focinho, bochechas, peito e orelha por dentro
        "b": "#2f231c",   # nariz e patas
    },
    "topo": (
        "...#...........#...",
        "..###.........###..",
        "..#a#.........#a#..",
    ),
    "detalhes": (volume, focinho, peito, patas),
}
