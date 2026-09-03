"""Regenera as imagens do mascote em `docs/`, a partir do codigo das skins.

Ferramenta de desenvolvimento, nao entra no widget: pede Pillow (`pip install
pillow`) e roda so quando o catalogo muda.

    python scripts/render_skins.py

Gera `docs/mascote.png` (o Classico, com fundo transparente) e
`docs/skins.png` (a folha com as dez). Desenhar aqui -- e nao a mao -- garante
que a documentacao mostre exatamente o que o widget desenha: as cores, os
acessorios e os detalhes saem de `ccwidget/skins/`, nao de uma copia.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from ccwidget import theme  # noqa: E402

FOLHA_ESCALA = 6
RETRATO_ESCALA = 8
FUNDO = (23, 22, 20)            # o #171614 do tema escuro
FUNDO_CELULA = "#201e1b"
TEXTO = (235, 231, 225)
COLUNAS = 5
MARGEM = 16
ROTULO = 20                     # faixa reservada ao nome, acima de cada figura


def _fonte(tamanho: int):
    for nome in ("segoeui.ttf", "DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            continue
    return ImageFont.load_default()


def _rgba(valor: str) -> tuple[int, int, int, int]:
    valor = valor.lstrip("#")
    return (*(int(valor[i:i + 2], 16) for i in (0, 2, 4)), 255)


def desenhar(
    skin: str, escala: int, altura_fixa: int | None = None, fundo: str | None = None
) -> Image.Image:
    """Uma skin parada, com o corpo alinhado pela base.

    Com `altura_fixa`, todas as figuras saem da mesma altura e o mascote de
    chapeu fica com os pes na mesma linha do sem chapeu. Sem `fundo`, o
    desenho sai em cima de transparencia.
    """
    theme.set_skin(skin)
    arte, _ = theme.compor_skin(theme.MASCOT)
    paleta = theme.cores_da_skin()
    principal = paleta["#"]

    alta = altura_fixa or len(arte)
    img = Image.new(
        "RGBA",
        (theme.MASCOT_W * escala, alta * escala),
        _rgba(fundo) if fundo else (0, 0, 0, 0),
    )
    pintor = ImageDraw.Draw(img)
    desce = alta - len(arte)
    for y, linha in enumerate(arte):
        for x, ch in enumerate(linha):
            if ch == ".":
                continue
            pintor.rectangle(
                [
                    x * escala, (y + desce) * escala,
                    (x + 1) * escala - 1, (y + desce + 1) * escala - 1,
                ],
                fill=_rgba(paleta.get(ch, principal)),
            )
    return img


def folha() -> Image.Image:
    """A folha de contato com as dez skins, cada uma sob o proprio nome."""
    altura_fixa = theme.MASCOT_H + theme.TOPO_MAX
    celula_w = theme.MASCOT_W * FOLHA_ESCALA
    celula_h = altura_fixa * FOLHA_ESCALA
    skins = list(theme.SKINS)
    linhas = -(-len(skins) // COLUNAS)

    largura = COLUNAS * celula_w + (COLUNAS + 1) * MARGEM
    altura = linhas * (celula_h + ROTULO) + (linhas + 1) * MARGEM
    img = Image.new("RGB", (largura, altura), FUNDO)
    pintor = ImageDraw.Draw(img)
    fonte = _fonte(12)

    for i, chave in enumerate(skins):
        linha, coluna = divmod(i, COLUNAS)
        x = MARGEM + coluna * (celula_w + MARGEM)
        y = MARGEM + linha * (celula_h + ROTULO + MARGEM)
        pintor.text((x, y), theme.SKINS[chave]["nome"], font=fonte, fill=TEXTO)
        figura = desenhar(chave, FOLHA_ESCALA, altura_fixa, FUNDO_CELULA)
        img.paste(figura, (x, y + ROTULO))
    return img


if __name__ == "__main__":
    docs = RAIZ / "docs"
    desenhar(theme.SKIN_PADRAO, RETRATO_ESCALA).save(docs / "mascote.png")
    folha().save(docs / "skins.png")
    print(f"docs/mascote.png e docs/skins.png ({len(theme.SKINS)} skins)")
