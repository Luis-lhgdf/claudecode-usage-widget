"""Widget flutuante de uso do Claude Code.

Janela sem bordas, sempre acima das outras, arrastavel para qualquer canto da
tela, montada com tkinter (biblioteca padrao -- nao ha nada para instalar).

Dois modos, alternados pelo menu da engrenagem:

* **mini**   -- so um circulo flutuante com o mascote e o anel da sessao.
* **painel** -- sessao de 5 horas e limite semanal, livre na tela.

Os numeros vem de uma unica fonte, a oficial: `claude -p "/usage"`. A consulta
acontece sozinha a cada dez minutos por padrao -- o intervalo e ajustavel pelo
menu -- e sob demanda no botao de atualizar. O widget nao estima consumo por
conta propria: sem dado, ele diz que nao tem dado.
"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from datetime import datetime

from . import __version__
from .config import Config, local_timezone
from .single_instance import serve
from .state import read_state
from .theme import (
    CHROMA,
    MASCOT_H,
    MASCOT_W,
    P,
    level_color,
    render_bar,
    render_bar_loading,
    render_dot,
    render_mascot,
    render_ring,
    set_theme,
)

PAD = 14
WIDTH = 268
RING_SIZE = 88

MODES = ("mini", "panel")
# Quadros do spinner: o tkinter nao rotaciona texto, entao a rotacao vem de
# uma sequencia de glifos.
SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
SPIN_MS = 70

# Abaixo de 40% de alfa o widget se dissolve no fundo e deixa de ser legivel.
# O controle continua indo de 1 a 100 para o usuario; e essa faixa que ele
# percorre de verdade.
OPACIDADE_MINIMA = 0.40
DAYS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def slider_para_alfa(valor: int) -> float:
    """Converte a posicao do controle (1 a 100) em opacidade real."""
    valor = min(max(valor, 1), 100)
    return OPACIDADE_MINIMA + (valor - 1) / 99 * (1.0 - OPACIDADE_MINIMA)


def alfa_para_slider(alfa: float) -> int:
    """Caminho inverso, para o controle abrir na posicao correspondente."""
    alfa = min(max(alfa, OPACIDADE_MINIMA), 1.0)
    return round(1 + (alfa - OPACIDADE_MINIMA) / (1.0 - OPACIDADE_MINIMA) * 99)


def fmt_duration_short(seconds: int) -> str:
    """Tempo ate o reset no circulo, onde cabem poucos caracteres: '3h18', '45m'."""
    if seconds <= 0:
        return "agora"
    minutes = seconds // 60
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}" if hours else f"{minutes}m"


def fmt_duration(seconds: int) -> str:
    """Duracao curta em portugues: '2h05', '17 min', 'agora'."""
    if seconds <= 0:
        return "agora"
    minutes = seconds // 60
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}"
    return f"{minutes} min"


class Mascot(tk.Canvas):
    """O mascote do Claude Code como widget."""

    def __init__(self, parent, scale: int = 1, bg: str | None = None) -> None:
        bg = bg or P["bg_soft"]
        super().__init__(
            parent, width=MASCOT_W * scale, height=MASCOT_H * scale,
            bg=bg, highlightthickness=0, bd=0,
        )
        self._scale = scale
        self._bg = bg
        # A referencia precisa sobreviver: o tkinter nao segura PhotoImage.
        self._image = render_mascot(scale, bg=bg)
        self._image_id = self.create_image(0, 0, image=self._image, anchor="nw")

    def set_frame(self, frame: int) -> None:
        """Troca o quadro da caminhada."""
        self._image = render_mascot(self._scale, bg=self._bg, frame=frame)
        self.itemconfigure(self._image_id, image=self._image)


class Ring(tk.Canvas):
    """Circulo do modo mini: mascote, percentual e tempo ate o reset.

    O disco e o anel sao rasterizados com antialiasing (`render_ring`), porque
    `create_oval` e `create_arc` do tkinter saem serrilhados.
    """

    def __init__(self, parent, size: int = RING_SIZE) -> None:
        super().__init__(
            parent, width=size, height=size, bg=CHROMA, highlightthickness=0, bd=0
        )
        self.size = size
        self._image = render_ring(size, None, P["ok"])
        self._image_id = self.create_image(0, 0, image=self._image, anchor="nw")

        # Alturas em fracao do diametro, com folga nas duas pontas: o mascote
        # nao encosta no anel e a hora nao encosta na base.
        self._mascot = render_mascot(2, bg=P["bg"])
        self._mascot_y = size * 0.30
        self._mascot_id = self.create_image(
            size / 2, self._mascot_y, image=self._mascot, anchor="center"
        )
        self._value = self.create_text(
            size / 2, size * 0.555, text="--", fill=P["fg"],
            font=("Segoe UI", 14, "bold"),
        )
        self._reset = self.create_text(
            size / 2, size * 0.765, text="", fill=P["fg_faint"],
            font=("Segoe UI", 8),
        )

    def set_loading(self, phase: float, frame: int = 0) -> None:
        """Anel girando e o mascote caminhando, enquanto o valor nao chega."""
        self._image = render_ring(self.size, 25, P["accent"], start=phase % 1.0)
        self.itemconfigure(self._image_id, image=self._image)
        self._set_mascot(frame)
        self.itemconfigure(self._value, text="···", fill=P["fg_faint"])
        self.itemconfigure(self._reset, text="")

    def _set_mascot(self, frame: int) -> None:
        self._mascot = render_mascot(2, bg=P["bg"], frame=frame)
        self.itemconfigure(self._mascot_id, image=self._mascot)
        # Sobe um pixel no quadro em que um pe esta no ar: sem isso a caminhada
        # fica so nos pes, e de longe nem se nota.
        salto = -1 if frame % 2 else 0
        self.coords(self._mascot_id, self.size / 2, self._mascot_y + salto)

    def set(self, pct: float | None, reset_text: str = "") -> None:
        color = P["ok"] if pct is None else level_color(pct)
        self._image = render_ring(self.size, pct, color)
        self.itemconfigure(self._image_id, image=self._image)
        self._set_mascot(0)
        if pct is None:
            self.itemconfigure(self._value, text="--", fill=P["fg_faint"])
        else:
            self.itemconfigure(self._value, text=f"{pct:.0f}%", fill=color)
        self.itemconfigure(self._reset, text=reset_text)


class Bar(tk.Canvas):
    """Barra de progresso em capsula, com pontas suavizadas."""

    HEIGHT = 7
    WIDTH = WIDTH - PAD * 2

    def __init__(self, parent) -> None:
        super().__init__(
            parent, height=self.HEIGHT, width=self.WIDTH,
            bg=P["bg"], highlightthickness=0, bd=0,
        )
        self._image = render_bar(self.WIDTH, self.HEIGHT, 0, P["ok"])
        self._image_id = self.create_image(0, 0, image=self._image, anchor="nw")

    def set(self, pct: float, color: str | None = None) -> None:
        pct = min(max(pct, 0.0), 100.0)
        self._image = render_bar(
            self.WIDTH, self.HEIGHT, pct, color or level_color(pct)
        )
        self.itemconfigure(self._image_id, image=self._image)

    def set_loading(self, phase: float) -> None:
        """Segmento correndo na pista, enquanto o valor novo nao chega."""
        self._image = render_bar_loading(
            self.WIDTH, self.HEIGHT, phase, P["accent"]
        )
        self.itemconfigure(self._image_id, image=self._image)


class Slider(tk.Canvas):
    """Controle deslizante desenhado a mao, no mesmo acabamento das barras."""

    ALTURA = 18
    PEGADOR = 14

    def __init__(self, parent, largura: int, valor: int, minimo: int, maximo: int,
                 ao_mudar) -> None:
        super().__init__(
            parent, width=largura, height=self.ALTURA,
            bg=P["bg"], highlightthickness=0, bd=0, cursor="hand2",
        )
        self.largura = largura
        self.minimo = minimo
        self.maximo = maximo
        self.valor = valor
        self.ao_mudar = ao_mudar

        # A trilha nao chega as bordas: o pegador precisa de espaco para nao
        # ser cortado nos extremos.
        self.margem = self.PEGADOR // 2
        self.trilha_larg = largura - self.PEGADOR
        self._trilha = render_bar(self.trilha_larg, 6, 0, P["accent"])
        self._trilha_id = self.create_image(
            self.margem, self.ALTURA / 2, image=self._trilha, anchor="w"
        )
        self._dot = render_dot(self.PEGADOR, P["accent"], P["bg"])
        self._dot_id = self.create_image(0, self.ALTURA / 2, image=self._dot, anchor="center")

        self.bind("<Button-1>", self._mover)
        self.bind("<B1-Motion>", self._mover)
        self._desenhar()

    def _fracao(self) -> float:
        return (self.valor - self.minimo) / max(self.maximo - self.minimo, 1)

    def _desenhar(self) -> None:
        fracao = self._fracao()
        self._trilha = render_bar(self.trilha_larg, 6, fracao * 100, P["accent"])
        self.itemconfigure(self._trilha_id, image=self._trilha)
        self.coords(
            self._dot_id, self.margem + fracao * self.trilha_larg, self.ALTURA / 2
        )

    def _mover(self, event) -> None:
        fracao = (event.x - self.margem) / max(self.trilha_larg, 1)
        fracao = min(max(fracao, 0.0), 1.0)
        novo = round(self.minimo + fracao * (self.maximo - self.minimo))
        if novo != self.valor:
            self.valor = novo
            self._desenhar()
            self.ao_mudar(novo)


class Meter(tk.Frame):
    """Titulo + percentual + barra + legenda: o bloco de uma janela de limite."""

    def __init__(self, parent, title: str) -> None:
        super().__init__(parent, bg=P["bg"])
        head = tk.Frame(self, bg=P["bg"])
        head.pack(fill="x")

        tk.Label(
            head, text=title, bg=P["bg"], fg=P["fg_dim"], anchor="w",
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")

        self.value = tk.Label(
            head, text="--", bg=P["bg"], fg=P["fg"], anchor="e",
            font=("Segoe UI", 12, "bold"),
        )
        self.value.pack(side="right")

        self.bar = Bar(self)
        self.bar.pack(fill="x", pady=(3, 3))

        # wraplength impede que uma legenda longa estique a largura do painel.
        self.caption = tk.Label(
            self, text="", bg=P["bg"], fg=P["fg_faint"], anchor="w", justify="left",
            font=("Segoe UI", 8), wraplength=WIDTH - PAD * 2,
        )
        self.caption.pack(fill="x")

    def set_loading(self, phase: float) -> None:
        self.value.configure(text="···", fg=P["fg_faint"])
        self.bar.set_loading(phase)

    def update_values(self, pct: float | None, caption: str) -> None:
        if pct is None:
            self.value.configure(text="--", fg=P["fg_faint"])
            self.bar.set(0)
        else:
            color = level_color(pct)
            self.value.configure(text=f"{pct:.0f}%", fg=color)
            self.bar.set(pct, color)
        self.caption.configure(text=caption)


class UsageWidget(tk.Tk):
    def __init__(self, instancia: object = None) -> None:
        super().__init__()
        # Socket reservado por single_instance: fica guardado para ser fechado
        # no fim e para atender os pedidos das outras copias.
        self._instancia = instancia
        self._pedido_foco = False
        self._popup_opacidade = None
        self._popup_opacidade = None
        self.cfg = Config.load()
        self.theme = set_theme(self.cfg.theme)
        self.tz = local_timezone()
        self.live = read_state()
        self.mode = self.cfg.mode if self.cfg.mode in MODES else "panel"
        self._drag = (0, 0)
        self._session_pct: float | None = None
        self._session_reset = ""
        self._cli_busy = False
        self._cli_error: str | None = None
        self._next_usage_at: float | None = None
        self._spin_frame = 0

        self._setup_window()
        self._build()
        self._apply_mode(self.mode, save=False)
        if instancia is not None:
            serve(instancia, self._marcar_pedido_foco)
        self.after(200, self._tick)
        self.after(250, self._atender_pedido_foco)
        self.after(600, self._schedule_usage)

    # ------------------------------------------------------------- estrutura

    def _setup_window(self) -> None:
        self.title("CC Widget")
        self.overrideredirect(True)  # sem barra de titulo do sistema
        self.configure(bg=P["bg"])
        self.attributes("-topmost", self.cfg.always_on_top)
        try:
            # Uma configuracao antiga pode trazer um valor abaixo do minimo; o
            # widget abriria invisivel e sem como ser ajustado.
            self.cfg.opacity = max(self.cfg.opacity, OPACIDADE_MINIMA)
            self.attributes("-alpha", self.cfg.opacity)
            # Deixa o canto do circulo transparente no modo mini.
            self.attributes("-transparentcolor", CHROMA)
        except tk.TclError:
            pass  # outros sistemas ignoram; o widget continua quadrado
        self.geometry(f"+{self.cfg.pos_x}+{self.cfg.pos_y}")

    def _build(self) -> None:
        self.container = tk.Frame(self, bg=CHROMA)
        self.container.pack(fill="both", expand=True)
        self._build_ring()
        self._build_panel()
        self._build_menu()

    def _build_ring(self) -> None:
        self.ring_holder = tk.Frame(self.container, bg=CHROMA)
        self.ring = Ring(self.ring_holder)
        self.ring.pack()
        self.ring.bind("<Button-1>", self._ring_press)
        self.ring.bind("<B1-Motion>", self._drag_move)
        self.ring.bind("<ButtonRelease-1>", self._ring_release)
        self.ring.bind("<Button-3>", self._show_menu)
        self.ring.configure(cursor="hand2")

    def _build_panel(self) -> None:
        # Borda de 1px: frame externo colorido com o conteudo por dentro.
        self.panel = tk.Frame(self.container, bg=P["border"])
        root = tk.Frame(self.panel, bg=P["bg"])
        root.pack(fill="both", expand=True, padx=1, pady=1)
        # Espacador de altura zero: fixa a largura do painel sem impedir que o
        # frame calcule a propria altura a partir dos filhos.
        tk.Frame(root, bg=P["bg"], width=WIDTH, height=0).pack()

        header = tk.Frame(root, bg=P["bg_soft"], height=38)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.header = header

        self.dot = Mascot(header, scale=1)
        self.dot.pack(side="left", padx=(PAD - 3, 7))
        self.heading = tk.Label(
            header, text="CC Widget", bg=P["bg_soft"], fg=P["fg"],
            font=("Segoe UI", 9, "bold"),
        )
        self.heading.pack(side="left")

        # O pack(side="right") empilha da direita para a esquerda, entao a
        # ordem abaixo e o inverso do que aparece na tela. Dois grupos: os
        # controles da janela na ponta, e as acoes do widget antes deles,
        # separados por um filete -- fechar e minimizar sao vizinhos perigosos
        # para um botao que se abre por engano.
        self._header_button(header, "✕", self.quit_widget, P["crit"])
        self._header_button(header, "─", lambda: self._apply_mode("mini"), P["accent"])
        tk.Frame(header, bg=P["ring_track"], width=1, height=15).pack(
            side="right", padx=5, pady=9
        )
        self._header_button(
            header, "⚙", self._show_menu_at_button, P["accent"], font_size=12
        )
        self.refresh_btn = self._header_button(
            header, "↻", self._kick_usage_cli, P["accent"], font_size=12
        )

        body = tk.Frame(root, bg=P["bg"])
        body.pack(fill="both", expand=True, padx=PAD, pady=(12, 4))

        self.session_meter = Meter(body, "SESSÃO ATUAL")
        self.session_meter.pack(fill="x")

        self.week_meter = Meter(body, "SEMANA")
        self.week_meter.pack(fill="x", pady=(13, 0))

        self.footer = tk.Label(
            root, text="", bg=P["bg"], fg=P["fg_faint"], anchor="w", justify="left",
            font=("Segoe UI", 7), wraplength=WIDTH - PAD * 2,
        )

        for widget in (header, self.dot, self.heading):
            widget.bind("<Button-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_move)
            widget.bind("<ButtonRelease-1>", self._drag_end)
            widget.bind("<Double-Button-1>", lambda _e: self._apply_mode("mini"))

        self.panel.bind("<Button-3>", self._show_menu)
        root.bind("<Button-3>", self._show_menu)
        self.bind("<Escape>", lambda _e: self.quit_widget())

    def _header_button(self, parent, text, command, hover, font_size=13):
        """Botao do cabecalho.

        O padding interno importa mais que o tamanho da fonte: e ele que da
        area de clique. O hover pinta o fundo, nao so o texto, para o alvo
        ficar visivel antes do clique.
        """
        btn = tk.Label(
            parent, text=text, bg=P["bg_soft"], fg=P["fg_dim"],
            font=("Segoe UI", font_size), cursor="hand2", padx=7, pady=3,
        )
        btn.pack(side="right", padx=1)
        btn.bind(
            "<Button-1>",
            lambda e: command(e) if _wants_event(command) else command(),
        )
        btn.bind("<Enter>", lambda _e: btn.configure(fg=hover, bg=P["border"]))
        btn.bind("<Leave>", lambda _e: btn.configure(fg=P["fg_dim"], bg=P["bg_soft"]))
        return btn

    def _build_menu(self) -> None:
        self.menu = tk.Menu(
            self, tearoff=0, bg=P["bg_soft"], fg=P["fg"], activebackground=P["accent"],
            activeforeground=P["menu_fg"], bd=0, font=("Segoe UI", 9),
        )
        self.var_mode = tk.StringVar(value=self.mode)
        self.var_theme = tk.StringVar(value=self.cfg.theme)
        self.var_top = tk.BooleanVar(value=self.cfg.always_on_top)
        self.var_interval = tk.IntVar(value=self.cfg.usage_refresh_minutes)

        for label, value in (("Minimizado", "mini"), ("Painel", "panel")):
            self.menu.add_radiobutton(
                label=label, value=value, variable=self.var_mode,
                command=lambda v=value: self._apply_mode(v),
            )
        self.menu.add_separator()
        self.menu.add_command(label="Atualizar agora", command=self._kick_usage_cli)

        theme_menu = tk.Menu(
            self.menu, tearoff=0, bg=P["bg_soft"], fg=P["fg"],
            activebackground=P["accent"], activeforeground=P["menu_fg"],
        )
        for label, value in (
            ("Do sistema", "auto"), ("Claro", "light"), ("Escuro", "dark")
        ):
            theme_menu.add_radiobutton(
                label=label, value=value, variable=self.var_theme,
                command=lambda v=value: self._apply_theme(v),
            )
        self.menu.add_cascade(label="Tema", menu=theme_menu)

        interval_menu = tk.Menu(
            self.menu, tearoff=0, bg=P["bg_soft"], fg=P["fg"],
            activebackground=P["accent"], activeforeground=P["menu_fg"],
        )
        for label, value in (
            ("5 minutos", 5),
            ("10 minutos", 10),
            ("15 minutos", 15),
            ("30 minutos", 30),
            ("1 hora", 60),
            ("Só manual", 0),
        ):
            interval_menu.add_radiobutton(
                label=label, value=value, variable=self.var_interval,
                command=lambda v=value: self._set_interval(v),
            )
        self.menu.add_cascade(label="Atualizar a cada", menu=interval_menu)

        self.menu.add_checkbutton(
            label="Sempre visível", variable=self.var_top, command=self._toggle_top
        )
        self.menu.add_command(label="Opacidade…", command=self._abrir_opacidade)
        self.menu.add_separator()
        self.menu.add_command(label="Fechar", command=self.quit_widget)
        self.menu.add_separator()
        self.menu.add_command(label=f"CC Widget {__version__}", state="disabled")

    # ------------------------------------------------------------------ modos

    def _apply_mode(self, mode: str, save: bool = True) -> None:
        if mode not in MODES:
            mode = "panel"
        self.mode = mode
        self.var_mode.set(mode)

        self.ring_holder.pack_forget()
        self.panel.pack_forget()
        self.footer.pack_forget()

        if mode == "mini":
            self.container.configure(bg=CHROMA)
            self.ring_holder.pack()
        else:
            self.container.configure(bg=P["bg"])
            self.panel.pack(fill="both", expand=True)
            self.footer.pack(fill="x", padx=PAD, pady=(10, 8))

        self._resize()
        if save:
            self.cfg.mode = mode
            self.cfg.save()
        self._render()

    def _apply_theme(self, name: str) -> None:
        """Troca a paleta reconstruindo a interface.

        Reconfigurar dezenas de widgets um a um deixaria cores esquecidas para
        tras; recriar o conteudo garante que tudo siga a paleta nova.
        """
        self.cfg.theme = name
        self.cfg.save()
        self.theme = set_theme(name)

        position = (self.winfo_x(), self.winfo_y())
        self.container.destroy()
        self.configure(bg=P["bg"])
        self._build()
        self._apply_mode(self.mode, save=False)
        self.geometry(f"+{position[0]}+{position[1]}")

    def _resize(self) -> None:
        """Reajusta a janela ao conteudo do modo atual.

        `geometry("")` devolve o dimensionamento ao tkinter, que mede o
        conteudo visivel; a posicao atual e preservada.
        """
        self.update_idletasks()
        self.geometry("")
        self.update_idletasks()

    # -------------------------------------------------------- copia unica

    def _marcar_pedido_foco(self) -> None:
        """Chamado da thread do listener: apenas sinaliza."""
        self._pedido_foco = True

    def _atender_pedido_foco(self) -> None:
        """Verifica o sinal na thread da interface, onde e seguro mexer na janela."""
        if self._pedido_foco:
            self._pedido_foco = False
            self._trazer_para_frente()
        self.after(250, self._atender_pedido_foco)

    def _trazer_para_frente(self) -> None:
        """Mostra a janela quando alguem tenta abrir uma segunda copia.

        Se a posicao salva ficou fora da area visivel -- monitor desconectado,
        por exemplo --, a janela volta para o canto da tela principal, senao o
        usuario clicaria no atalho sem ver nada acontecer.
        """
        if self._fora_da_tela():
            self.geometry("+40+40")
            self.cfg.pos_x, self.cfg.pos_y = 40, 40
            self.cfg.save()

        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.update_idletasks()
        if not self.cfg.always_on_top:
            self.attributes("-topmost", False)

    def _fora_da_tela(self) -> bool:
        """A janela esta fora de qualquer monitor?"""
        x, y = self.winfo_x(), self.winfo_y()
        largura, altura = self.winfo_width(), self.winfo_height()
        # winfo_vroot* cobre a area de trabalho inteira, com varios monitores.
        vx, vy = self.winfo_vrootx(), self.winfo_vrooty()
        vw, vh = self.winfo_vrootwidth(), self.winfo_vrootheight()
        return (
            x + largura < vx or x > vx + vw
            or y + altura < vy or y > vy + vh
        )

    # ---------------------------------------------------------- interacoes

    def _drag_start(self, event) -> None:
        self._drag = (event.x_root - self.winfo_x(), event.y_root - self.winfo_y())

    def _drag_move(self, event) -> None:
        self.geometry(f"+{event.x_root - self._drag[0]}+{event.y_root - self._drag[1]}")

    def _drag_end(self, _event=None) -> None:
        self.cfg.pos_x = self.winfo_x()
        self.cfg.pos_y = self.winfo_y()
        self.cfg.save()

    def _ring_press(self, event) -> None:
        self._drag_start(event)
        self._drag_origin = (event.x_root, event.y_root)

    def _ring_release(self, event) -> None:
        """Clique sem arrastar abre o painel; arrastar so reposiciona."""
        origin = getattr(self, "_drag_origin", (event.x_root, event.y_root))
        moved = abs(event.x_root - origin[0]) + abs(event.y_root - origin[1])
        self._drag_end()
        if moved < 5:
            self._apply_mode("panel")

    def _show_menu(self, event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _show_menu_at_button(self, event) -> None:
        widget = event.widget
        try:
            self.menu.tk_popup(
                widget.winfo_rootx(), widget.winfo_rooty() + widget.winfo_height() + 2
            )
        finally:
            self.menu.grab_release()

    def _set_interval(self, minutes: int) -> None:
        """Troca o intervalo entre consultas automaticas, pelo menu."""
        self.cfg.usage_refresh_minutes = minutes
        self.cfg.save()
        self._next_usage_at = time.time() + minutes * 60 if minutes else None
        self._render_footer()

    def _toggle_top(self) -> None:
        self.cfg.always_on_top = self.var_top.get()
        self.attributes("-topmost", self.cfg.always_on_top)
        self.cfg.save()

    def _set_opacity(self, value: float) -> None:
        self.cfg.opacity = value
        try:
            self.attributes("-alpha", value)
        except tk.TclError:
            pass

    def _abrir_opacidade(self) -> None:
        """Janelinha com o controle deslizante de 1 a 100%.

        Ela propria fica sempre opaca: com o widget em 1% seria impossivel
        enxergar o controle para desfazer o ajuste.
        """
        if getattr(self, "_popup_opacidade", None) is not None:
            try:
                self._popup_opacidade.destroy()
            except tk.TclError:
                pass

        popup = tk.Toplevel(self)
        self._popup_opacidade = popup
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg=P["border"])

        corpo = tk.Frame(popup, bg=P["bg"])
        corpo.pack(fill="both", expand=True, padx=1, pady=1)

        topo = tk.Frame(corpo, bg=P["bg"])
        topo.pack(fill="x", padx=PAD, pady=(10, 0))
        tk.Label(
            topo, text="OPACIDADE", bg=P["bg"], fg=P["fg_dim"],
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")
        rotulo = tk.Label(
            topo, text=f"{alfa_para_slider(self.cfg.opacity)}%", bg=P["bg"],
            fg=P["fg"], font=("Segoe UI", 11, "bold"),
        )
        rotulo.pack(side="right")

        def mudou(valor: int) -> None:
            rotulo.configure(text=f"{valor}%")
            self._set_opacity(slider_para_alfa(valor))

        largura = WIDTH - PAD * 2
        Slider(
            corpo, largura, alfa_para_slider(self.cfg.opacity), 1, 100, mudou
        ).pack(padx=PAD, pady=(8, 4))

        tk.Label(
            corpo, text="Esc ou clique fora para fechar", bg=P["bg"],
            fg=P["fg_faint"], font=("Segoe UI", 7),
        ).pack(pady=(0, 9))

        def fechar(_evento=None) -> None:
            self.cfg.save()
            self._popup_opacidade = None
            popup.destroy()

        popup.bind("<Escape>", fechar)
        popup.bind("<FocusOut>", fechar)
        popup.update_idletasks()
        popup.geometry(f"+{self.winfo_x()}+{self.winfo_y() + self.winfo_height() + 6}")
        popup.focus_force()

    def quit_widget(self, _event=None) -> None:
        self.cfg.pos_x = self.winfo_x()
        self.cfg.pos_y = self.winfo_y()
        self.cfg.save()
        if self._instancia is not None:
            try:
                self._instancia.close()
            except OSError:
                pass
        self.destroy()

    # ------------------------------------------------------------ atualizacao

    def _tick(self) -> None:
        """Redesenha periodicamente, para o tempo ate o reset ficar correndo."""
        self.live = read_state()
        self._render()
        self.after(max(self.cfg.refresh_seconds, 5) * 1000, self._tick)

    def _schedule_usage(self) -> None:
        """Consulta o /usage se o dado estiver velho, e reagenda."""
        minutes = max(int(self.cfg.usage_refresh_minutes or 0), 0)
        if not minutes:
            return
        if self.live.age_seconds > minutes * 60:
            self._kick_usage_cli()
        self._next_usage_at = time.time() + minutes * 60
        self.after(minutes * 60_000, self._schedule_usage)

    def _kick_usage_cli(self) -> None:
        """Busca os percentuais rodando `claude -p /usage` numa thread.

        E a unica fonte de dados do widget. O comando e local -- nao ha
        resposta de modelo, entao nao consome tokens -- mas leva alguns
        segundos para o CLI iniciar, por isso nunca roda no laco da interface.
        """
        if self._cli_busy:
            return
        self._cli_busy = True
        self._cli_error = None
        self._spin_frame = 0
        self._animate_loading()
        threading.Thread(target=self._usage_cli_worker, daemon=True).start()

    def _animate_loading(self) -> None:
        """Enquanto o /usage responde: seta girando e barras indeterminadas.

        A consulta leva alguns segundos, e sem sinal de atividade o clique no
        botao parece nao ter feito nada. Os valores antigos saem de cena porque
        deixaram de valer no instante em que a consulta comecou.

        Este laco tambem e quem encerra o carregamento. A thread de trabalho
        apenas baixa `_cli_busy`: tkinter nao e seguro para uso concorrente, e
        agendar a volta de la deixava a interface presa no estado de carregando
        quando o callback se perdia.
        """
        if not self._cli_busy:
            self.refresh_btn.configure(text="↻", fg=P["fg_dim"])
            if self.mode != "mini":
                self.dot.set_frame(0)
            self._refresh_now()
            return

        self._spin_frame += 1
        phase = (self._spin_frame % 40) / 40
        # Um passo a cada dois quadros: na cadencia do spinner o mascote
        # pareceria correr.
        passo = self._spin_frame // 2
        self.refresh_btn.configure(
            text=SPINNER[self._spin_frame % len(SPINNER)], fg=P["accent"]
        )

        if self.mode == "mini":
            self.ring.set_loading(phase, passo)
        else:
            self.dot.set_frame(passo)
            self.session_meter.set_loading(phase)
            self.week_meter.set_loading((phase + 0.5) % 1.0)
            self._render_footer()

        self.after(SPIN_MS, self._animate_loading)

    def _usage_cli_worker(self) -> None:
        from .usage_cli import refresh_state

        try:
            refresh_state()
        except Exception as exc:
            self._cli_error = str(exc)
        finally:
            # So isto: quem redesenha e `_animate_loading`, na thread da
            # interface. Nada de tocar em widgets a partir daqui.
            self._cli_busy = False

    def _refresh_now(self) -> None:
        self.live = read_state()
        self.refresh_btn.configure(text="↻", fg=P["fg_dim"])
        self._render()

    def _render(self) -> None:
        self._render_session()
        self._render_week()
        if self.mode == "mini":
            self.ring.set(self._session_pct, self._session_reset)
        else:
            self._render_footer()

    def _render_session(self) -> None:
        window = self.live.five_hour
        if window is not None and window.expired:
            window = None

        if window is None:
            self._session_pct = None
            self._session_reset = ""
            self.session_meter.update_values(None, "Sem dado · menu › Atualizar agora")
            return

        self._session_pct = window.used_percentage
        # No circulo cabe pouco: so o tempo que falta, sem a palavra "reinicia".
        self._session_reset = fmt_duration_short(window.remaining_seconds())
        caption = f"Reinicia em {fmt_duration(window.remaining_seconds())}"
        if window.resets_at:
            clock = datetime.fromtimestamp(window.resets_at, tz=self.tz)
            caption += f" · {clock:%H:%M}"
        self.session_meter.update_values(window.used_percentage, caption)

    def _render_week(self) -> None:
        window = self.live.seven_day
        if window is not None and window.expired:
            window = None

        if window is None:
            self.week_meter.update_values(None, "Sem dado")
            return

        caption = "Todos os modelos"
        if window.resets_at:
            clock = datetime.fromtimestamp(window.resets_at, tz=self.tz)
            caption = f"Reinicia {DAYS[clock.weekday()]} {clock:%d/%m} · {clock:%H:%M}"
        self.week_meter.update_values(window.used_percentage, caption)

    def _render_footer(self) -> None:
        """Rodape: quando o dado foi lido e quando sera lido de novo."""
        if self._cli_busy:
            self.footer.configure(text="consultando /usage…", fg=P["fg_dim"])
            return

        if self._cli_error:
            self.footer.configure(text=f"falhou: {self._cli_error}", fg=P["crit"])
            return
        if not self.live.available:
            self.footer.configure(
                text="sem dados ainda · clique em ↻", fg=P["fg_faint"]
            )
            return

        age = int(self.live.age_seconds)
        texto = (
            "Atualizado agora há pouco"
            if age < 60
            else f"Atualizado há {fmt_duration(age)}"
        )

        if self._next_usage_at:
            falta = int(self._next_usage_at - time.time())
            if falta > 0:
                texto += f" · próxima em {fmt_duration(falta)}"

        self.footer.configure(
            text=texto, fg=P["warn"] if self.live.stale else P["fg_faint"]
        )


def _wants_event(func) -> bool:
    """Callbacks de botao recebem o evento so quando declaram um parametro."""
    try:
        from inspect import signature

        return len(signature(func).parameters) >= 1
    except (TypeError, ValueError):
        return False


def run() -> None:
    """Abre o widget, ou traz para frente a copia que ja estiver aberta."""
    from .single_instance import claim, wake_existing

    instancia = claim()
    if instancia is None:
        if wake_existing():
            return  # ja havia uma copia; ela veio para frente
        # A porta esta ocupada por outro programa: seguimos sem a protecao.
    UsageWidget(instancia).mainloop()
