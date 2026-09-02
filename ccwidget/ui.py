"""Widget flutuante de uso do Claude Code.

Janela sem bordas, sempre acima das outras, arrastavel para qualquer canto da
tela, montada com tkinter (biblioteca padrao -- nao ha nada para instalar).

Tres modos, alternados pelo menu da engrenagem:

* **mini**   -- so um circulo flutuante com o mascote e o anel da sessao.
* **gaveta** -- encostado na borda direita da tela, mostrando so uma abinha;
  um clique nela desliza o painel para dentro da tela.
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

from .config import Config, local_timezone
from .state import LiveState, read_state
from .theme import (
    CHROMA,
    MASCOT_H,
    MASCOT_W,
    P,
    level_color,
    render_mascot,
    set_theme,
)

PAD = 14
WIDTH = 268
RING_SIZE = 64

MODES = ("mini", "drawer", "panel")
DAYS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")

DRAWER_TAB = 20      # largura da abinha que fica visivel na borda da tela
DRAWER_STEPS = 12    # quadros da animacao de abrir e fechar
DRAWER_FRAME_MS = 12


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
        # A referencia precisa sobreviver: o tkinter nao segura PhotoImage.
        self._image = render_mascot(scale, bg=bg)
        self.create_image(0, 0, image=self._image, anchor="nw")


class Ring(tk.Canvas):
    """Circulo do modo mini: mascote, percentual e anel de progresso."""

    def __init__(self, parent, size: int = RING_SIZE) -> None:
        super().__init__(
            parent, width=size, height=size, bg=CHROMA, highlightthickness=0, bd=0
        )
        pad = 4
        box = (pad, pad, size - pad, size - pad)

        # Disco de fundo, para o conteudo ter contraste sobre qualquer janela.
        self.create_oval(1, 1, size - 1, size - 1, fill=P["bg"], outline=P["border"])
        self.create_arc(
            *box, start=90, extent=-359.9, style="arc", width=4,
            outline=P["ring_track"],
        )
        self._arc = self.create_arc(
            *box, start=90, extent=0, style="arc", width=4, outline=P["ok"]
        )
        self._mascot = render_mascot(1, bg=P["bg"])
        self.create_image(size / 2, size * 0.34, image=self._mascot, anchor="center")
        self._value = self.create_text(
            size / 2, size * 0.63, text="--", fill=P["fg"],
            font=("Segoe UI", 11, "bold"),
        )
        self.create_text(
            size / 2, size * 0.80, text="5h", fill=P["fg_faint"],
            font=("Segoe UI", 6),
        )

    def set(self, pct: float | None) -> None:
        if pct is None:
            self.itemconfigure(self._arc, extent=0)
            self.itemconfigure(self._value, text="--", fill=P["fg_faint"])
            return
        pct = min(max(pct, 0.0), 100.0)
        color = level_color(pct)
        # -0.1 evita o arco cheio virar circulo fechado sem inicio visivel.
        self.itemconfigure(self._arc, extent=-(pct * 3.599 or 0.1), outline=color)
        self.itemconfigure(self._value, text=f"{pct:.0f}%", fill=color)


class Bar(tk.Canvas):
    """Barra de progresso fina, redesenhada quando a largura muda."""

    HEIGHT = 6

    def __init__(self, parent) -> None:
        # A largura inicial importa: sem ela o Canvas assume o padrao do tkinter
        # (378px) e estica o painel inteiro. O <Configure> cuida do resto.
        super().__init__(
            parent, height=self.HEIGHT, width=WIDTH - PAD * 2,
            bg=P["bg"], highlightthickness=0, bd=0,
        )
        self._pct = 0.0
        self._color = P["ok"]
        self._track = self.create_rectangle(
            0, 0, 0, self.HEIGHT, fill=P["track"], outline=""
        )
        self._fill = self.create_rectangle(
            0, 0, 0, self.HEIGHT, fill=P["ok"], outline=""
        )
        self.bind("<Configure>", lambda _e: self._draw())

    def _draw(self) -> None:
        width = max(self.winfo_width(), 1)
        self.coords(self._track, 0, 0, width, self.HEIGHT)
        filled = int(width * self._pct / 100)
        if self._pct > 0:
            filled = max(filled, 2)
        self.coords(self._fill, 0, 0, filled, self.HEIGHT)
        self.itemconfigure(self._fill, fill=self._color)

    def set(self, pct: float, color: str | None = None) -> None:
        self._pct = min(max(pct, 0.0), 100.0)
        self._color = color or level_color(self._pct)
        self._draw()


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
    def __init__(self) -> None:
        super().__init__()
        self.cfg = Config.load()
        self.theme = set_theme(self.cfg.theme)
        self.tz = local_timezone()
        self.live = read_state()
        self.mode = self.cfg.mode if self.cfg.mode in MODES else "panel"
        self._drag = (0, 0)
        self._session_pct: float | None = None
        self._cli_busy = False
        self._cli_error: str | None = None
        self._next_usage_at: float | None = None
        self._drawer_open = False

        self._setup_window()
        self._build()
        self._apply_mode(self.mode, save=False)
        self.after(200, self._tick)
        self.after(600, self._schedule_usage)

    # ------------------------------------------------------------- estrutura

    def _setup_window(self) -> None:
        self.title("CC Widget")
        self.overrideredirect(True)  # sem barra de titulo do sistema
        self.configure(bg=P["bg"])
        self.attributes("-topmost", self.cfg.always_on_top)
        try:
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
        self._build_tab()
        self._build_menu()

    def _build_tab(self) -> None:
        """A abinha do modo gaveta: a alca que fica visivel na borda da tela."""
        # Borda propria: encostada no painel, a aba precisa de um contorno para
        # nao virar uma extensao dele, e de contorno tambem quando esta sozinha
        # na borda da tela, sobre qualquer janela por baixo.
        self.tab = tk.Frame(self.container, bg=P["border"], width=DRAWER_TAB)
        self.tab.pack_propagate(False)

        face = tk.Frame(self.tab, bg=P["bg_soft"])
        face.pack(fill="both", expand=True, padx=(1, 0), pady=1)

        inner = tk.Frame(face, bg=P["bg_soft"])
        inner.place(relx=0.5, rely=0.5, anchor="center")

        self.tab_mascot = Mascot(inner, scale=1)
        self.tab_mascot.pack(pady=(0, 6))
        # A seta aponta para onde a gaveta vai: para dentro quando fechada,
        # para a borda quando aberta.
        self.tab_arrow = tk.Label(
            inner, text="‹", bg=P["bg_soft"], fg=P["fg_dim"], font=("Segoe UI", 12)
        )
        self.tab_arrow.pack()

        for widget in (self.tab, face, inner, self.tab_mascot, self.tab_arrow):
            widget.configure(cursor="hand2")
            widget.bind("<Button-1>", self._tab_press)
            widget.bind("<B1-Motion>", self._tab_drag)
            widget.bind("<ButtonRelease-1>", self._tab_release)
            widget.bind("<Button-3>", self._show_menu)

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

        for label, value in (
            ("Minimizado", "mini"), ("Gaveta", "drawer"), ("Painel", "panel")
        ):
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
        opacity = tk.Menu(
            self.menu, tearoff=0, bg=P["bg_soft"], fg=P["fg"],
            activebackground=P["accent"], activeforeground=P["menu_fg"],
        )
        for label, value in (("100%", 1.0), ("96%", 0.96), ("85%", 0.85), ("70%", 0.70)):
            opacity.add_command(label=label, command=lambda v=value: self._set_opacity(v))
        self.menu.add_cascade(label="Opacidade", menu=opacity)
        self.menu.add_separator()
        self.menu.add_command(label="Fechar", command=self.quit_widget)

    # ------------------------------------------------------------------ modos

    def _apply_mode(self, mode: str, save: bool = True) -> None:
        if mode not in MODES:
            mode = "panel"
        anterior = self.mode
        self.mode = mode
        self.var_mode.set(mode)

        self.ring_holder.pack_forget()
        self.panel.pack_forget()
        self.tab.pack_forget()
        self.footer.pack_forget()

        if mode == "mini":
            self.container.configure(bg=CHROMA)
            self.ring_holder.pack()
        else:
            self.container.configure(bg=P["bg"])
            self.footer.pack(fill="x", padx=PAD, pady=(10, 8))
            if mode == "drawer":
                # A aba vai na direita, colada na borda da tela; o painel
                # desliza para dentro e para fora atras dela.
                self.tab.pack(side="right", fill="y")
                self.panel.pack(side="left", fill="both", expand=True)
            else:
                self.panel.pack(fill="both", expand=True)

        self._resize()

        if mode == "drawer":
            self._drawer_open = False
            self._snap_drawer(animate=False)
        elif anterior == "drawer":
            # Sai da borda e volta para a posicao livre guardada.
            self.geometry(f"+{self.cfg.pos_x}+{self.cfg.pos_y}")

        if save:
            self.cfg.mode = mode
            self.cfg.save()
        self._render()

    # ------------------------------------------------------------------ gaveta

    def _drawer_x(self, aberto: bool) -> int:
        """X da janela com a gaveta aberta ou fechada.

        Fechada, so a abinha fica dentro da tela: o resto da janela fica para
        fora, o que o Windows permite e e justamente o efeito de gaveta.
        """
        largura = self.winfo_width() or (WIDTH + DRAWER_TAB + 2)
        tela = self.winfo_screenwidth()
        return tela - largura if aberto else tela - DRAWER_TAB

    def _snap_drawer(self, animate: bool = True) -> None:
        alvo = self._drawer_x(self._drawer_open)
        self.tab_arrow.configure(text="›" if self._drawer_open else "‹")
        if animate:
            self._slide_to(alvo)
        else:
            self.geometry(f"+{alvo}+{self.cfg.drawer_y}")

    def _slide_to(self, alvo: int, passo: int = 0) -> None:
        """Anima o deslize com desaceleracao no fim."""
        if passo >= DRAWER_STEPS:
            self.geometry(f"+{alvo}+{self.winfo_y()}")
            return
        inicio = self.winfo_x()
        # ease-out: avanca mais no comeco e chega devagar
        fracao = 1 - (1 - (passo + 1) / DRAWER_STEPS) ** 3
        atual = int(inicio + (alvo - inicio) * fracao / max(1 - fracao + 0.0001, 0.35))
        self.geometry(f"+{min(max(atual, min(inicio, alvo)), max(inicio, alvo))}+{self.winfo_y()}")
        self.after(DRAWER_FRAME_MS, lambda: self._slide_to(alvo, passo + 1))

    def _toggle_drawer(self) -> None:
        self._drawer_open = not self._drawer_open
        self._snap_drawer()

    def _tab_press(self, event) -> None:
        self._drag_start(event)
        self._drag_origin = (event.x_root, event.y_root)

    def _tab_drag(self, event) -> None:
        """Na gaveta so o movimento vertical faz sentido: o X fica na borda."""
        y = event.y_root - self._drag[1]
        self.geometry(f"+{self.winfo_x()}+{y}")

    def _tab_release(self, event) -> None:
        origin = getattr(self, "_drag_origin", (event.x_root, event.y_root))
        moved = abs(event.x_root - origin[0]) + abs(event.y_root - origin[1])
        self.cfg.drawer_y = self.winfo_y()
        self.cfg.save()
        if moved < 5:
            self._toggle_drawer()

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
        self.cfg.save()

    def quit_widget(self, _event=None) -> None:
        self.cfg.pos_x = self.winfo_x()
        self.cfg.pos_y = self.winfo_y()
        self.cfg.save()
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
        self._render_footer()
        threading.Thread(target=self._usage_cli_worker, daemon=True).start()

    def _usage_cli_worker(self) -> None:
        from .usage_cli import refresh_state

        try:
            refresh_state()
        except Exception as exc:
            self._cli_error = str(exc)
        finally:
            self._cli_busy = False
        try:
            self.after(0, self._refresh_now)
        except RuntimeError:
            pass  # janela ja fechada

    def _refresh_now(self) -> None:
        self.live = read_state()
        self._render()

    def _render(self) -> None:
        self._render_session()
        self._render_week()
        if self.mode == "mini":
            self.ring.set(self._session_pct)
        else:
            self._render_footer()

    def _render_session(self) -> None:
        window = self.live.five_hour
        if window is not None and window.expired:
            window = None

        if window is None:
            self._session_pct = None
            self.session_meter.update_values(None, "Sem dado · menu › Atualizar agora")
            return

        self._session_pct = window.used_percentage
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
        """Rodape: quando o dado foi lido e quando sera lido de novo.

        Substitui o antigo selo "oficial/antigo", que descrevia a fonte numa
        epoca em que havia duas. Com uma fonte so, o que resta a informar e a
        idade do numero -- e isso e melhor dito com o tempo do que com rotulo.
        """
        if self._cli_busy:
            self.refresh_btn.configure(fg=P["accent"])
            self.footer.configure(text="consultando /usage…", fg=P["fg_dim"])
            return

        self.refresh_btn.configure(fg=P["fg_dim"])

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
    UsageWidget().mainloop()
