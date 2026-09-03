"""Alienígena: antenas com bulbo, olhos amendoados e uma boca de risco."""

from .base import corpo, volume


def olhos_grandes(linhas) -> None:
    """Contorno escuro em volta dos vaos: o olho amendoado do alienigena.

    O contorno e a moldura; o vao no meio dele e a pupila. Quando uma pose
    fecha os olhos, sobra a orbita -- que e exatamente o que se espera.
    """
    corpo(linhas, (1, 5), (4, 5, 13, 14), "a")
    corpo(linhas, (2, 3, 4), (3, 6, 12, 15), "a")


def boca_fina(linhas) -> None:
    """Boca minuscula, so um risco entre as duas orbitas."""
    corpo(linhas, (5,), (8, 9, 10), "a")


SKIN = {
    "nome": "Alienígena",
    "resumo": "Antenas com bulbo, olhos amendoados e uma boca de risco.",
    "cores": {
        "#": "#9370c4", "s": "#6f4f9c", "l": "#c3a4e6",
        "a": "#1c1426",   # orbitas e boca
        "b": "#c9f279",   # bulbo das antenas
    },
    "topo": (
        "...b...........b...",
        "....s.........s....",
        ".....s.......s.....",
    ),
    "detalhes": (volume, olhos_grandes, boca_fina),
}
