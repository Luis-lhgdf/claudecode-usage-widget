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
    "..##..#######..##..",
    "..##..#######..##..",
    "..##..#######..##..",
    "..###############..",
    "###################",
    "###################",
    "..###############..",
    "..###############..",
    "..##..##...##..##..",
    "..##..##...##..##..",
)

MASCOT_W = len(MASCOT[0])
MASCOT_H = len(MASCOT)

# Passos da caminhada: a ultima linha guarda as duas pontas das pernas, e
# recolher uma de cada vez da a impressao de passo. Os quadros pares deixam as
# duas no chao, para o movimento ter um ponto de apoio entre as passadas.
MASCOT_STEPS = 4


# Linhas onde ficam os bracos (as pontas que passam do corpo) e para onde o
# braco direito sobe no aceno.
BRACO_LINHAS = (6, 7)
BRACO_ERGUIDO = (4, 5)
BRACO_COLUNAS = (17, 18)


# Os olhos sao dois vaos verticais no corpo; preenche-los fecha as palpebras.
OLHO_LINHA = 2
OLHO_LINHAS = (2, 3, 4)
OLHO_COLUNAS = (4, 5, 13, 14)


def mascot_blink() -> tuple[str, ...]:
    """Mascote de olhos fechados."""
    linhas = [list(l) for l in MASCOT]
    for y in OLHO_LINHAS:
        for x in OLHO_COLUNAS:
            linhas[y][x] = "#"
    return tuple("".join(l) for l in linhas)


def mascot_wave(frame: int) -> tuple[str, ...]:
    """Mascote acenando: o braco direito sobe e desce.

    O aceno reaproveita as pontas que ja passam do corpo -- e o unico traco do
    desenho que pode se mover sem descaracterizar a figura.
    """
    linhas = [list(l) for l in MASCOT]
    if frame % 2:
        for y in BRACO_LINHAS:
            for x in BRACO_COLUNAS:
                linhas[y][x] = "."
        for y in BRACO_ERGUIDO:
            for x in BRACO_COLUNAS:
                linhas[y][x] = "#"
    return tuple("".join(l) for l in linhas)


def mascot_frame(frame: int) -> tuple[str, ...]:
    """Variacao do mascote para o quadro pedido da caminhada."""
    fase = frame % MASCOT_STEPS
    if fase == 0 or fase == 2:
        return MASCOT
    linhas = list(MASCOT)
    ultima = linhas[-1]
    if fase == 1:  # pe direito no ar
        linhas[-1] = "".join(
            ch if i < len(ultima) // 2 else "." for i, ch in enumerate(ultima)
        )
    else:          # pe esquerdo no ar
        linhas[-1] = "".join(
            ch if i > len(ultima) // 2 else "." for i, ch in enumerate(ultima)
        )
    return tuple(linhas)


_MASCOT_CACHE: dict[tuple, tk.PhotoImage] = {}


# ------------------------------------------------------------------ skins

# Uma skin muda a cor do mascote, pode pintar detalhes dentro do corpo e pode
# acrescentar um "topo" -- chapeu, antenas, orelhas -- desenhado acima dele.
#
# O corpo continua sendo o MASCOT de 19x12, e e nele que as poses mexem. O topo
# entra so na hora de desenhar, entao acessorio nenhum atrapalha as animacoes.
#
# Na arte, cada caractere e uma cor: "#" e a cor principal e as letras sao
# cores extras declaradas pela skin. "." e vazio.

SKINS: dict[str, dict] = {
    "classico": {
        "nome": "Clássico",
        "cores": {"#": "#d97757"},
    },
    "monstro": {
        "nome": "Monstro",
        "cores": {"#": "#7a9e4f", "a": "#5d7a3c"},
        "detalhe": "espinhos",
    },
    "robo": {
        "nome": "Robô",
        "cores": {"#": "#5b86b5", "a": "#8fc2e8", "b": "#d97757"},
        "topo": ("........#..........", "......aaaaa........"),
        "detalhe": "visor",
    },
    "alien": {
        "nome": "Alienígena",
        "cores": {"#": "#8b6bb1", "a": "#c9a6e8"},
        "topo": ("....a.......a......", ".....a.....a......."),
    },
    "ninja": {
        "nome": "Ninja",
        "cores": {"#": "#33343d", "a": "#c0392b", "b": "#e8c9a0"},
        "detalhe": "faixa",
    },
    "esqueleto": {
        "nome": "Esqueleto",
        "cores": {"#": "#e6e2d3", "a": "#b8b1a0"},
        "detalhe": "costelas",
    },
    "mago": {
        "nome": "Mago",
        "cores": {"#": "#7b5ea7", "a": "#5a4180", "b": "#f2c14e"},
        "topo": (".......aaa.........", "......aaaaa........"),
        "detalhe": "estrela",
    },
    "pirata": {
        "nome": "Pirata",
        "cores": {"#": "#d97757", "a": "#2f3136", "b": "#e6e2d3"},
        "topo": ("....aaaaaaaaa......", "...aaaaaaaaaaa....."),
        "detalhe": "tapa_olho",
    },
    "raposa": {
        "nome": "Raposa",
        "cores": {"#": "#e07b39", "a": "#f5ead6", "b": "#3a2b22"},
        "topo": ("..##.........##....", "..##.........##...."),
        "detalhe": "focinho",
    },
    "cavaleiro": {
        "nome": "Cavaleiro",
        "cores": {"#": "#9aa2ab", "a": "#6c737c", "b": "#c0392b"},
        "topo": (".......bbb.........", "....aaaaaaaaa......"),
        "detalhe": "viseira",
    },
}

SKIN_PADRAO = "classico"


def _detalhe_espinhos(linhas) -> None:
    """Serrilha as bordas laterais, como as pontas do monstro."""
    for y in (1, 3, 5, 8):
        linhas[y][2] = "a"
        linhas[y][16] = "a"


def _detalhe_visor(linhas) -> None:
    """Faixa clara ligando os olhos, como o visor de um robo."""
    meio = OLHO_LINHAS[1]
    for x in range(6, 13):
        linhas[meio][x] = "a"


def _detalhe_faixa(linhas) -> None:
    """Faixa do ninja passando por tras dos olhos."""
    meio = OLHO_LINHAS[1]
    for x in range(2, 17):
        if linhas[meio][x] == "#":
            linhas[meio][x] = "a"


def _detalhe_costelas(linhas) -> None:
    """Riscos no tronco, para lembrar uma caixa toracica."""
    for y in (8, 9):
        for x in (6, 9, 12):
            linhas[y][x] = "a"


def _detalhe_estrela(linhas) -> None:
    """Um ponto dourado no peito do mago."""
    linhas[8][9] = "b"


def _detalhe_tapa_olho(linhas) -> None:
    """Cobre o olho esquerdo e deixa a correia atravessada."""
    for y in OLHO_LINHAS:
        for x in OLHOS_PADRAO[0]:
            linhas[y][x] = "a"
    linhas[OLHO_LINHAS[0]][3] = "a"
    linhas[OLHO_LINHAS[0]][6] = "a"


def _detalhe_focinho(linhas) -> None:
    """Focinho claro na parte de baixo do rosto."""
    for x in range(7, 12):
        linhas[5][x] = "a"
    linhas[5][9] = "b"


def _detalhe_viseira(linhas) -> None:
    """Fendas verticais da viseira do elmo."""
    meio = OLHO_LINHAS[1]
    for x in range(6, 13):
        linhas[meio][x] = "a"
    for x in (7, 9, 11):
        for y in OLHO_LINHAS:
            linhas[y][x] = "a"


DETALHES = {
    "espinhos": _detalhe_espinhos,
    "visor": _detalhe_visor,
    "faixa": _detalhe_faixa,
    "costelas": _detalhe_costelas,
    "estrela": _detalhe_estrela,
    "tapa_olho": _detalhe_tapa_olho,
    "focinho": _detalhe_focinho,
    "viseira": _detalhe_viseira,
}

_SKIN_ATUAL = SKIN_PADRAO


def set_skin(nome: str) -> str:
    """Escolhe a skin ativa. Devolve a que ficou valendo."""
    global _SKIN_ATUAL
    _SKIN_ATUAL = nome if nome in SKINS else SKIN_PADRAO
    _MASCOT_CACHE.clear()      # as imagens guardam as cores da skin
    return _SKIN_ATUAL


def get_skin() -> str:
    return _SKIN_ATUAL


def compor_skin(arte: tuple[str, ...], skin: str | None = None):
    """Junta corpo, detalhes e topo da skin.

    Devolve as linhas e quantas delas sao de acessorio, porque o desenho
    precisa subir para o topo caber sem empurrar o corpo para baixo.
    """
    dados = SKINS.get(skin or _SKIN_ATUAL, SKINS[SKIN_PADRAO])

    linhas = [list(l) for l in arte]
    detalhe = dados.get("detalhe")
    if detalhe:
        DETALHES[detalhe](linhas)

    topo = [list(l) for l in dados.get("topo", ())]
    return tuple("".join(l) for l in topo + linhas), len(topo)


def cores_da_skin(skin: str | None = None) -> dict:
    dados = SKINS.get(skin or _SKIN_ATUAL, SKINS[SKIN_PADRAO])
    return dados["cores"]


def pintar(arte: tuple[str, ...], scale: int, bg: str, skin: str | None = None):
    """Rasteriza uma arte ja composta, usando as cores da skin."""
    cores = cores_da_skin(skin)
    principal = cores.get("#", P["accent"])
    largura = max(len(l) for l in arte)

    rows = []
    for linha in arte:
        pixels = []
        for x in range(largura):
            ch = linha[x] if x < len(linha) else "."
            pixels.append(bg if ch == "." else cores.get(ch, principal))
        row = "{" + " ".join(p for p in pixels for _ in range(scale)) + "}"
        rows.extend([row] * scale)

    imagem = tk.PhotoImage(width=largura * scale, height=len(arte) * scale)
    imagem.put(" ".join(rows))
    return imagem


def render_mascot(
    scale: int = 1,
    color: str | None = None,
    bg: str | None = None,
    frame: int = 0,
    wave: bool = False,
    blink: bool = False,
):
    """Mascote na skin ativa, ampliado por um fator inteiro.

    Devolve so a imagem, para quem nao se importa com o acessorio; use
    `render_mascot_off` quando precisar do deslocamento que o topo exige.
    """
    imagem, _ = render_mascot_off(scale, color, bg, frame, wave, blink)
    return imagem


def render_mascot_off(
    scale: int = 1,
    color: str | None = None,
    bg: str | None = None,
    frame: int = 0,
    wave: bool = False,
    blink: bool = False,
):
    """Como `render_mascot`, mas tambem diz quanto subir a imagem.

    Uma skin com chapeu ou antenas rende uma imagem mais alta. Centrada como
    esta, ela empurraria o corpo para baixo; o deslocamento devolvido aqui
    recoloca o corpo onde estava.
    """
    bg = bg or P["bg_soft"]
    if blink:
        arte = mascot_blink()
    elif wave:
        arte = mascot_wave(frame)
    else:
        arte = mascot_frame(frame)

    composta, linhas_topo = compor_skin(arte)
    key = (
        "m", scale, bg, frame % MASCOT_STEPS, wave, blink, get_skin(),
        color or "",
    )
    imagem = _MASCOT_CACHE.get(key)
    if imagem is None:
        imagem = pintar(composta, scale, bg)
        _MASCOT_CACHE[key] = imagem
    return imagem, -(linhas_topo * scale) / 2


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


def render_dot(size: int, color: str, bg: str, samples: int = 4) -> tk.PhotoImage:
    """Disco cheio, suavizado. Usado como pegador do controle de opacidade."""
    key = ("dot", size, color, bg, samples)
    cached = _SHAPE_CACHE.get(key)
    if cached is not None:
        return cached

    import math

    centro = size / 2
    raio = centro - 0.5
    fg = _hex_to_rgb(color)
    fundo = _hex_to_rgb(bg)
    step = 1.0 / samples
    total = samples * samples

    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            dentro = 0
            for sy in range(samples):
                dy = py + (sy + 0.5) * step - centro
                for sx in range(samples):
                    dx = px + (sx + 0.5) * step - centro
                    if math.hypot(dx, dy) <= raio:
                        dentro += 1
            row.append(bg if not dentro else _blend(fg, fundo, dentro / total))
        rows.append("{" + " ".join(row) + "}")

    image = tk.PhotoImage(width=size, height=size)
    image.put(" ".join(rows))
    _SHAPE_CACHE[key] = image
    return image


# ------------------------------------------------------------------ poses

# O mascote tem 19x12 blocos, e quase tudo nele e corpo cheio. Os unicos
# tracos que podem mudar sem descaracterizar a figura sao os vaos (os olhos) e
# as pontas que passam do corpo (os bracos e os pes). Todas as poses abaixo
# trabalham sobre esses tres elementos, mais o deslocamento da figura inteira.

OLHOS_PADRAO = ((4, 5), (13, 14))
CORPO_ESQ, CORPO_DIR = 2, 16      # limites em que um vao ainda cai no corpo


def _base() -> list[list[str]]:
    return [list(l) for l in MASCOT]


def _tapar_olhos(linhas: list[list[str]]) -> None:
    for y in OLHO_LINHAS:
        for lado in OLHOS_PADRAO:
            for x in lado:
                linhas[y][x] = "#"


def _abrir_olhos(linhas, esquerdo, direito, alturas=OLHO_LINHAS) -> None:
    """Abre vaos nas posicoes dadas, respeitando as bordas do corpo."""
    for y in alturas:
        if not 0 <= y < len(linhas):
            continue
        for x in tuple(esquerdo) + tuple(direito):
            if CORPO_ESQ <= x <= CORPO_DIR:
                linhas[y][x] = "."


def _erguer_bracos(linhas, esquerdo=True, direito=True) -> None:
    if direito:
        for y in BRACO_LINHAS:
            for x in BRACO_COLUNAS:
                linhas[y][x] = "."
        for y in BRACO_ERGUIDO:
            for x in BRACO_COLUNAS:
                linhas[y][x] = "#"
    if esquerdo:
        for y in BRACO_LINHAS:
            for x in (0, 1):
                linhas[y][x] = "."
        for y in BRACO_ERGUIDO:
            for x in (0, 1):
                linhas[y][x] = "#"


def _montar(linhas) -> tuple[str, ...]:
    return tuple("".join(l) for l in linhas)


def pose_olhar(quadro: int):
    """Olha para um lado, volta, olha para o outro."""
    etapa = quadro % 8
    linhas = _base()
    _tapar_olhos(linhas)
    if etapa in (0, 1):            # esquerda
        _abrir_olhos(linhas, (3, 4), (12, 13))
    elif etapa in (4, 5):          # direita
        _abrir_olhos(linhas, (5, 6), (14, 15))
    else:                          # centro
        _abrir_olhos(linhas, *OLHOS_PADRAO)
    return _montar(linhas), 0, 0


def pose_oculos(quadro: int):
    """Poe e tira um par de oculos: vaos maiores, em duas alturas."""
    linhas = _base()
    if quadro % 8 < 6:             # de oculos na maior parte do tempo
        _tapar_olhos(linhas)
        _abrir_olhos(linhas, (3, 4, 5), (12, 13, 14))
        linhas[OLHO_LINHA + 1][9] = "."   # a ponte entre as lentes
    return _montar(linhas), 0, 0


def pose_sono(quadro: int):
    """Olhos semicerrados e corpo pesando para baixo."""
    linhas = _base()
    _tapar_olhos(linhas)
    if quadro % 6 < 4:
        _abrir_olhos(linhas, (4,), (14,), alturas=(OLHO_LINHA + 1,))  # so uma fresta
        return _montar(linhas), 0, 1
    _abrir_olhos(linhas, *OLHOS_PADRAO)
    return _montar(linhas), 0, 0


def pose_surpresa(quadro: int):
    """Olhos arregalados e um pulinho de susto."""
    linhas = _base()
    _tapar_olhos(linhas)
    if quadro % 6 < 4:
        _abrir_olhos(linhas, (3, 4, 5), (13, 14, 15))
        return _montar(linhas), 0, -2
    _abrir_olhos(linhas, *OLHOS_PADRAO)
    return _montar(linhas), 0, 0


def pose_piscadela(quadro: int):
    """Fecha so um olho."""
    linhas = _base()
    if quadro % 4 < 2:
        for y in OLHO_LINHAS:
            for x in OLHOS_PADRAO[0]:
                linhas[y][x] = "#"
    return _montar(linhas), 0, 0


def pose_bracos(quadro: int):
    """Levanta os dois bracos, como quem se espreguica."""
    linhas = _base()
    if quadro % 4 < 2:
        _erguer_bracos(linhas)
    return _montar(linhas), 0, 0


def pose_pular(quadro: int):
    """Dois pulos, com os pes recolhidos no ar."""
    altura = (0, -3, -5, -3, 0, -3, -5, -3)[quadro % 8]
    linhas = _base()
    if altura < 0:                  # no ar as pernas se recolhem
        for y in (10, 11):
            for x in range(len(linhas[y])):
                linhas[y][x] = "." if linhas[y][x] == "#" else linhas[y][x]
        for y in (10, 11):
            for x in (7, 8, 10, 11):
                linhas[y][x] = "#"
    return _montar(linhas), 0, altura


def pose_dancar(quadro: int):
    """Bamboleia de um lado para o outro."""
    desloca = (-3, 0, 3, 0)[quadro % 4]
    return _montar(_base()), desloca, 0


def pose_sacudir(quadro: int):
    """Tremida curta, como um arrepio."""
    desloca = (-2, 2, -2, 2, -1, 1, 0, 0)[quadro % 8]
    return _montar(_base()), desloca, 0


def pose_cochilar(quadro: int):
    """Fecha os olhos por um tempo e desperta."""
    linhas = _base()
    if quadro % 10 < 7:
        _tapar_olhos(linhas)
        return _montar(linhas), 0, 1
    return _montar(linhas), 0, 0


def pose_espiar(quadro: int):
    """Espia para um lado e volta depressa, como quem ouviu algo."""
    etapa = quadro % 6
    linhas = _base()
    _tapar_olhos(linhas)
    if etapa < 3:
        _abrir_olhos(linhas, (5, 6), (14, 15))
        return _montar(linhas), 2, 0
    _abrir_olhos(linhas, *OLHOS_PADRAO)
    return _montar(linhas), 0, 0


def pose_feliz(quadro: int):
    """Olhos apertados, o `> <` que o mascote faz nas artes oficiais.

    Cada olho vira uma diagonal: o vao desce uma linha no meio e volta, o que
    em tres linhas ja le como um olho fechado de contentamento.
    """
    linhas = _base()
    _tapar_olhos(linhas)
    if quadro % 6 < 4:
        topo, meio, base = OLHO_LINHAS
        linhas[topo][4] = linhas[base][4] = "."      # esquerdo: >
        linhas[meio][5] = "."
        linhas[topo][14] = linhas[base][14] = "."    # direito: <
        linhas[meio][13] = "."
    else:
        _abrir_olhos(linhas, *OLHOS_PADRAO)
    return _montar(linhas), 0, 0


def pose_oculos_sol(quadro: int):
    """Baixa um par de oculos escuros: uma barra sobre os dois olhos."""
    linhas = _base()
    if quadro % 8 < 6:
        _tapar_olhos(linhas)
        meio = OLHO_LINHAS[1]
        for x in range(3, 16):                        # a barra das lentes
            linhas[meio][x] = "."
        for x in (3, 4, 5, 13, 14, 15):               # as lentes, mais altas
            linhas[meio - 1][x] = "."
            linhas[meio + 1][x] = "."
    else:
        _abrir_olhos(linhas, *OLHOS_PADRAO)
    return _montar(linhas), 0, 0


def pose_piscar(quadro: int):
    """Fecha e abre os dois olhos."""
    linhas = _base()
    if quadro % 2 == 0:
        _tapar_olhos(linhas)
    return _montar(linhas), 0, 0


def pose_oi(quadro: int):
    """Acena com o braco direito."""
    return mascot_wave(quadro // 2), 0, 0


def pose_passos(quadro: int):
    """Pisa no lugar, alternando os pes."""
    return mascot_frame(quadro), 0, (-1 if quadro % 2 else 0)


POSES = {
    "feliz": pose_feliz,
    "oculos_sol": pose_oculos_sol,
    "piscar": pose_piscar,
    "oi": pose_oi,
    "passos": pose_passos,
    "olhar": pose_olhar,
    "oculos": pose_oculos,
    "sono": pose_sono,
    "surpresa": pose_surpresa,
    "piscadela": pose_piscadela,
    "bracos": pose_bracos,
    "pular": pose_pular,
    "dancar": pose_dancar,
    "sacudir": pose_sacudir,
    "cochilar": pose_cochilar,
    "espiar": pose_espiar,
}


def render_pose(pose: str, quadro: int, scale: int = 2, bg: str | None = None):
    """Imagem de uma pose na skin ativa, com o deslocamento que ela pede."""
    arte, dx, dy = POSES[pose](quadro)
    bg = bg or P["bg"]
    composta, linhas_topo = compor_skin(arte)

    key = ("pose", pose, quadro, scale, bg, get_skin())
    imagem = _MASCOT_CACHE.get(key)
    if imagem is None:
        imagem = pintar(composta, scale, bg)
        _MASCOT_CACHE[key] = imagem
    return imagem, dx * scale, dy * scale - (linhas_topo * scale) / 2
