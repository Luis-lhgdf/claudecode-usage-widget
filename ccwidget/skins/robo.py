"""Robô: antena acesa, visor de vidro e um painel de luzes no peito."""

from .base import corpo, sobrepor, volume


def visor(linhas) -> None:
    """Visor de vidro claro emoldurado por metal escuro.

    Os olhos continuam sendo os vaos do corpo: contra o vidro claro eles ficam
    ate mais nitidos do que ficariam contra a chapa.
    """
    corpo(linhas, (1,), range(3, 16), "a")        # aro de cima
    corpo(linhas, (2, 3, 4), range(3, 16), "l")   # o vidro
    corpo(linhas, (5,), range(3, 16), "a")        # aro de baixo


def grelha(linhas) -> None:
    """Grelha do alto-falante, logo abaixo do visor."""
    corpo(linhas, (6,), range(6, 13), "s")
    corpo(linhas, (6,), (7, 9, 11), "a")


def painel(linhas) -> None:
    """Painel no peito: tres luzes e um mostrador."""
    corpo(linhas, (8, 9), range(6, 13), "a")
    sobrepor(linhas, (8,), (7, 9, 11), "b")
    sobrepor(linhas, (9,), range(7, 12), "s")


def juntas(linhas) -> None:
    """Bracos em metal mais escuro que o corpo, como pecas encaixadas."""
    corpo(linhas, (6, 7), (0, 1, 17, 18), "s")


SKIN = {
    "nome": "Robô",
    "resumo": "Antena acesa, visor de vidro e um painel de luzes no peito.",
    "cores": {
        "#": "#6d9dc9", "s": "#41607e", "l": "#c6e5f8",
        "a": "#26374a",   # chapa escura: aros, grelha e painel
        "b": "#f2b33d",   # luzes do painel
        "c": "#e05c4b",   # lampada da antena
    },
    "topo": (
        ".........c.........",
        ".........a.........",
        "........aaa........",
    ),
    "detalhes": (volume, visor, grelha, painel, juntas),
}
