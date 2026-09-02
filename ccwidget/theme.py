"""Paletas do widget e o mascote do Claude Code.

As cores ficam num dicionario global (`P`) trocado por `set_theme`. Os
componentes leem a paleta na construcao, entao alternar o tema reconstroi a
interface -- mais simples e confiavel do que reconfigurar dezenas de widgets.
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
