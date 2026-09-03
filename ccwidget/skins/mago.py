"""Mago: chapeu de ponta com estrela, barba longa e cinto dourado."""

from .base import corpo, sobrepor, volume


def chapeu(linhas) -> None:
    """A base do cone e a aba, pintadas ja dentro da cabeca.

    O topo tem tres linhas de teto; descer o chapeu mais duas pelo corpo e o
    que da a ele altura de mago em vez de altura de bone.
    """
    corpo(linhas, (0,), range(3, 16), "a")
    corpo(linhas, (1,), range(2, 17), "a")


def barba(linhas) -> None:
    """Barba longa, descendo do rosto ate o peito."""
    corpo(linhas, (5,), range(5, 14), "b")
    corpo(linhas, (6, 7), range(7, 12), "b")
    corpo(linhas, (8,), range(8, 11), "b")


def cinto(linhas) -> None:
    """Cinto do manto, com a fivela dourada."""
    corpo(linhas, (9,), range(2, 17), "a")
    sobrepor(linhas, (9,), (9,), "c")


def estrelas(linhas) -> None:
    """Duas estrelas bordadas no manto."""
    corpo(linhas, (8,), (4, 14), "c")


SKIN = {
    "nome": "Mago",
    "resumo": "Chapéu de ponta com estrela, barba longa e cinto dourado.",
    "cores": {
        "#": "#7b5ea7", "s": "#5b4480", "l": "#9a7cc4",
        "a": "#3a2b5c",   # chapeu e cinto
        "b": "#efe9de",   # barba
        "c": "#f2c14e",   # estrelas e fivela
    },
    "topo": (
        ".........a.........",
        "........aaa........",
        ".......aacaa.......",
    ),
    "detalhes": (volume, chapeu, barba, cinto, estrelas),
}
