"""Catalogo de skins do mascote.

Cada personagem mora no proprio modulo e exporta um `SKIN`. Para acrescentar
um, basta criar o arquivo e citar o modulo em `_MODULOS`: a ordem da tupla e a
ordem em que as skins aparecem no menu.

Uma skin e um dicionario com:

    nome       o rotulo do menu
    resumo     uma linha dizendo o que a veste
    cores      caractere -> cor; "#" e o corpo, "s" a sombra, "l" a luz
    topo       (opcional) ate `TOPO_MAX` linhas de arte acima da cabeca
    detalhes   funcoes que pintam dentro do corpo, na ordem em que rodam
"""

from __future__ import annotations

from . import (
    alien,
    cavaleiro,
    classico,
    esqueleto,
    mago,
    monstro,
    ninja,
    pirata,
    raposa,
    robo,
)
from .base import CORPO_CHARS, TOPO_MAX, corpo, sobrepor, volume

_MODULOS = (
    classico, monstro, robo, alien, ninja,
    esqueleto, mago, pirata, raposa, cavaleiro,
)

# A chave e o nome do modulo, e e ela que vai parar na configuracao do usuario.
SKINS: dict[str, dict] = {
    modulo.__name__.rsplit(".", 1)[-1]: modulo.SKIN for modulo in _MODULOS
}

SKIN_PADRAO = "classico"

__all__ = [
    "CORPO_CHARS",
    "SKINS",
    "SKIN_PADRAO",
    "TOPO_MAX",
    "compor",
    "cores",
    "corpo",
    "sobrepor",
    "volume",
]


def compor(arte: tuple[str, ...], skin: str):
    """Junta corpo, detalhes e topo da skin.

    Devolve as linhas e quantas delas sao de acessorio, porque o desenho
    precisa subir para o topo caber sem empurrar o corpo para baixo.
    """
    dados = SKINS.get(skin, SKINS[SKIN_PADRAO])

    linhas = [list(l) for l in arte]
    for detalhe in dados.get("detalhes", ()):
        detalhe(linhas)

    topo = [list(l) for l in dados.get("topo", ())]
    return tuple("".join(l) for l in topo + linhas), len(topo)


def cores(skin: str) -> dict[str, str]:
    return SKINS.get(skin, SKINS[SKIN_PADRAO])["cores"]
