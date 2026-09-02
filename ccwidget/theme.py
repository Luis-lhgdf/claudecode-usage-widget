"""Paletas, mascote e as formas desenhadas do widget.

As cores ficam num dicionario global (`P`) trocado por `set_theme`. Os
componentes leem a paleta na construcao, entao alternar o tema reconstroi a
interface -- mais simples e confiavel do que reconfigurar dezenas de widgets.

Aqui tambem ficam o mascote (pixel art) e as formas curvas -- disco, anel e
barras --, rasterizadas com antialiasing proprio porque o Canvas do tkinter
nao suaviza bordas.
"""

from __future__ import annotations

import tkinter as tk

# Cor que o Windows torna transparente no modo mini: precisa ser uma que nunca
# apareca no desenho real, senao buracos aparecem no widget.
CHROMA = "#ff00fe"

ACCENT = "#d97757"  # o salmao do mascote, igual nos dois temas

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#171614",
        "bg_soft": "#201e1b",
        "border": "#332f2a",
        "fg": "#ebe7e1",
        "fg_dim": "#8b8378",
        "fg_faint": "#5f594f",
        "track": "#2c2925",
        "ring_track": "#3b352d",
        "accent": ACCENT,
        "ok": "#7fa66a",
        "warn": "#d8a244",
        "crit": "#d1614f",
        "neutral": "#6f6759",
        "menu_fg": "#1a1613",
    },
    "light": {
        "bg": "#faf8f5",
        "bg_soft": "#efebe4",
        "border": "#ded7cb",
        "fg": "#2a2724",
        "fg_dim": "#6d6659",
        "fg_faint": "#9a9184",
        "track": "#e4ded3",
        "ring_track": "#d5cec2",
        "accent": ACCENT,
        # Tons mais escuros que os do tema escuro: sobre fundo claro, as cores
        # vivas do outro tema nao alcancam contraste suficiente.
        "ok": "#4d7a3a",
        "warn": "#9c6c14",
        "crit": "#b03f2d",
        "neutral": "#8d8477",
        "menu_fg": "#faf8f5",
    },
}

P: dict[str, str] = dict(THEMES["dark"])


def detect_system_theme() -> str:
    """Le a preferencia do Windows. Cai para 'dark' se nao der para saber."""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        with key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return "light" if value else "dark"
    except Exception:
        return "dark"


def resolve_theme(name: str) -> str:
    """Converte 'auto' na preferencia do sistema."""
    if name == "auto":
        return detect_system_theme()
    return name if name in THEMES else "dark"


def set_theme(name: str) -> str:
    """Ativa uma paleta. Devolve o tema efetivamente aplicado."""
    resolved = resolve_theme(name)
    P.clear()
    P.update(THEMES[resolved])
    _MASCOT_CACHE.clear()  # as imagens carregam a cor de fundo do tema
    return resolved


def level_color(pct: float) -> str:
    if pct >= 85:
        return P["crit"]
    if pct >= 60:
        return P["warn"]
    return P["ok"]


# --------------------------------------------------------------- mascote

# O mascote do Claude Code, extraido da arte que o proprio CLI exibe no
# cabecalho. Como e pixel art, ampliar por um fator inteiro mantem as bordas
# nitidas -- nao ha necessidade de antialiasing.
MASCOT = (
    "..###############..",
    "..###############..",
    "..###############..",
    "..##..#######..##..",
    "..###############..",
    "###################",
    "###################",
    "..###############..",
    "..###############..",
    "....####...####....",
    ".......#...#.......",
    ".......#...#.......",
)

MASCOT_W = len(MASCOT[0])
MASCOT_H = len(MASCOT)

_MASCOT_CACHE: dict[tuple, tk.PhotoImage] = {}


def render_mascot(
    scale: int = 1, color: str | None = None, bg: str | None = None
) -> tk.PhotoImage:
    """Devolve o mascote como imagem, ampliado por um fator inteiro.

    O resultado fica em cache por (escala, cor, fundo): montar a imagem custa
    mais do que exibi-la, e o widget a redesenha a cada atualizacao.
    """
    color = color or P["accent"]
    bg = bg or P["bg_soft"]
    key = (scale, color, bg)
    cached = _MASCOT_CACHE.get(key)
    if cached is not None:
        return cached

    rows = []
    for line in MASCOT:
        pixels = [color if ch == "#" else bg for ch in line]
        row = "{" + " ".join(p for p in pixels for _ in range(scale)) + "}"
        rows.extend([row] * scale)

    image = tk.PhotoImage(width=MASCOT_W * scale, height=MASCOT_H * scale)
    image.put(" ".join(rows))
    _MASCOT_CACHE[key] = image
    return image


# ------------------------------------------------- formas com antialiasing

# O Canvas do tkinter nao suaviza bordas: `create_oval` e `create_arc` saem
# serrilhados, e e isso que da o aspecto pixelado do circulo. As funcoes abaixo
# rasterizam as formas amostrando cada pixel numa grade `samples x samples`,
# como o CustomTkinter faz por outro caminho (glifos de uma fonte de formas),
# mas sem depender de biblioteca externa.

_SHAPE_CACHE: dict[tuple, tk.PhotoImage] = {}


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _blend(fg: tuple[int, int, int], bg: tuple[int, int, int], a: float) -> str:
    return "#%02x%02x%02x" % (
        round(bg[0] + (fg[0] - bg[0]) * a),
        round(bg[1] + (fg[1] - bg[1]) * a),
        round(bg[2] + (fg[2] - bg[2]) * a),
    )


def render_ring(
    size: int,
    pct: float | None,
    arc_color: str,
    outside: str = CHROMA,
    samples: int = 4,
    start: float = 0.0,
) -> tk.PhotoImage:
    """Disco com anel de progresso, suavizado.

    A borda externa e decidida por maioria (dentro ou fora) em vez de misturada
    com `outside`: como a cor de fora vira transparencia no Windows, uma mistura
    ali deixaria uma franja magenta em volta do circulo. Ja o anel, a pista e o
    fundo -- todos internos -- sao misturados normalmente.
    """
    pct = -1.0 if pct is None else min(max(pct, 0.0), 100.0)
    key = (
        "ring", size, round(pct), round(start, 3), arc_color,
        P["bg"], P["border"], P["ring_track"],
    )
    cached = _SHAPE_CACHE.get(key)
    if cached is not None:
        return cached

    import math

    center = size / 2
    r_out = center - 0.5          # borda do disco
    r_border = r_out - 1.2        # espessura da borda
    ring_out = r_out - 2.5        # faixa do anel de progresso
    ring_in = ring_out - 4.5

    bg = _hex_to_rgb(P["bg"])
    border = _hex_to_rgb(P["border"])
    track = _hex_to_rgb(P["ring_track"])
    arc = _hex_to_rgb(arc_color)
    step = 1.0 / samples
    total = samples * samples
    limite = pct / 100 if pct >= 0 else -1.0

    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            dentro = 0
            acc = [0.0, 0.0, 0.0]
            for sy in range(samples):
                dy = py + (sy + 0.5) * step - center
                for sx in range(samples):
                    dx = px + (sx + 0.5) * step - center
                    dist = math.hypot(dx, dy)
                    if dist > r_out:
                        continue
                    dentro += 1
                    if dist > r_border:
                        cor = border
                    elif ring_in <= dist <= ring_out:
                        # angulo medido do topo, no sentido horario
                        t = ((math.atan2(dy, dx) + math.pi / 2) % (2 * math.pi)) / (
                            2 * math.pi
                        )
                        # O arco corre de `start` por `limite` de volta, o que
                        # permite gira-lo durante o carregamento.
                        rel = (t - start) % 1.0
                        cor = arc if 0 <= rel <= limite else track
                    else:
                        cor = bg
                    acc[0] += cor[0]
                    acc[1] += cor[1]
                    acc[2] += cor[2]
            if dentro * 2 <= total:      # maioria fora: pixel transparente
                row.append(outside)
            else:
                row.append(
                    "#%02x%02x%02x"
                    % (
                        round(acc[0] / dentro),
                        round(acc[1] / dentro),
                        round(acc[2] / dentro),
                    )
                )
        rows.append("{" + " ".join(row) + "}")

    image = tk.PhotoImage(width=size, height=size)
    image.put(" ".join(rows))
    _SHAPE_CACHE[key] = image
    return image


def render_bar(
    width: int, height: int, pct: float, color: str, samples: int = 4
) -> tk.PhotoImage:
    """Barra em capsula (cantos arredondados), suavizada nas pontas."""
    pct = min(max(pct, 0.0), 100.0)
    key = ("bar", width, height, round(pct, 1), color, P["bg"], P["track"])
    cached = _SHAPE_CACHE.get(key)
    if cached is not None:
        return cached

    import math

    raio = height / 2
    preenchido = width * pct / 100
    bg = _hex_to_rgb(P["bg"])
    track = _hex_to_rgb(P["track"])
    fill = _hex_to_rgb(color)
    step = 1.0 / samples
    total = samples * samples

    def dentro_capsula(x: float, y: float, limite: float) -> bool:
        """Retangulo com semicirculos nas pontas."""
        if limite <= 0:
            return False
        if x < raio:
            return math.hypot(x - raio, y - raio) <= raio
        if x > limite - raio:
            return math.hypot(x - (limite - raio), y - raio) <= raio
        return True

    rows = []
    for py in range(height):
        row = []
        for px in range(width):
            n_track = n_fill = 0
            for sy in range(samples):
                y = py + (sy + 0.5) * step
                for sx in range(samples):
                    x = px + (sx + 0.5) * step
                    if not dentro_capsula(x, y, width):
                        continue
                    n_track += 1
                    if preenchido >= height and dentro_capsula(x, y, preenchido):
                        n_fill += 1
            if not n_track:
                row.append(P["bg"])
                continue
            cor = _blend(track, bg, n_track / total)
            if n_fill:
                cor = _blend(fill, _hex_to_rgb(cor), n_fill / n_track)
            row.append(cor)
        rows.append("{" + " ".join(row) + "}")

    image = tk.PhotoImage(width=width, height=height)
    image.put(" ".join(rows))
    _SHAPE_CACHE[key] = image
    return image


def render_bar_loading(
    width: int, height: int, phase: float, color: str, samples: int = 3
) -> tk.PhotoImage:
    """Barra indeterminada: um segmento que percorre a pista.

    Usada enquanto o `/usage` responde -- o valor antigo ja nao vale, e o novo
    ainda nao chegou, entao nao ha percentual honesto para mostrar.

    A fase e quantizada antes de virar chave de cache: sao poucas imagens
    reaproveitadas em todo ciclo da animacao.
    """
    import math

    phase = phase % 1.0
    key = ("barload", width, height, round(phase, 2), color, P["bg"], P["track"])
    cached = _SHAPE_CACHE.get(key)
    if cached is not None:
        return cached

    raio = height / 2
    seg = width * 0.3
    # O segmento entra pela esquerda e sai pela direita.
    x0 = -seg + (width + seg) * phase
    x1 = x0 + seg

    bg = _hex_to_rgb(P["bg"])
    track = _hex_to_rgb(P["track"])
    fill = _hex_to_rgb(color)
    step = 1.0 / samples
    total = samples * samples

    def na_pista(x: float, y: float) -> bool:
        if x < raio:
            return math.hypot(x - raio, y - raio) <= raio
        if x > width - raio:
            return math.hypot(x - (width - raio), y - raio) <= raio
        return 0 <= x <= width

    rows = []
    for py in range(height):
        row = []
        for px in range(width):
            n_track = n_seg = 0
            for sy in range(samples):
                y = py + (sy + 0.5) * step
                for sx in range(samples):
                    x = px + (sx + 0.5) * step
                    if not na_pista(x, y):
                        continue
                    n_track += 1
                    if x0 <= x <= x1:
                        n_seg += 1
            if not n_track:
                row.append(P["bg"])
                continue
            cor = _blend(track, bg, n_track / total)
            if n_seg:
                # Desvanece nas pontas do segmento, para o movimento nao piscar.
                centro = (x0 + x1) / 2
                dist = abs(px + 0.5 - centro) / (seg / 2)
                alpha = max(0.0, 1.0 - dist ** 2) * (n_seg / n_track)
                cor = _blend(fill, _hex_to_rgb(cor), alpha)
            row.append(cor)
        rows.append("{" + " ".join(row) + "}")

    image = tk.PhotoImage(width=width, height=height)
    image.put(" ".join(rows))
    _SHAPE_CACHE[key] = image
    return image
