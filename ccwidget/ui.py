"""Widget flutuante de uso do Claude Code.

Janela sem bordas, sempre acima das outras, arrastavel para qualquer canto da
tela, montada com tkinter (biblioteca padrao -- nao ha nada para instalar).

Tres modos, alternados pelo botao de menu no topo ou por duplo clique:

* **mini**    -- so um circulo flutuante com o anel de progresso da sessao.
* **resumo**  -- sessao de 5 horas e limite semanal.
* **completo**-- acrescenta tokens, valor equivalente e ranking de projetos.

Duas fontes alimentam a tela:

* **Oficial** -- percentuais e horarios de reset publicados pela ponte de
  status line (`ccwidget.statusline`). Sao os mesmos numeros do `/usage`.
* **Local**   -- tokens, valor equivalente e projetos, calculados dos logs de
  sessao. Aparecem sempre, e viram fallback quando o oficial falta.

Tudo que e estimado leva o prefixo `~`, para nao se confundir com dado oficial.
"""

from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime, timedelta, timezone

from .analytics import current_block, group_by, week_period
from .collector import Collector
from .config import Config, local_timezone
from .state import LiveState, read_state

# ---------------------------------------------------------------- aparencia

BG = "#171614"
BG_SOFT = "#201e1b"
BORDER = "#332f2a"
FG = "#ebe7e1"
FG_DIM = "#8b8378"
FG_FAINT = "#5f594f"
ACCENT = "#d97757"
TRACK = "#2c2925"

OK = "#7fa66a"
WARN = "#d8a244"
CRIT = "#d1614f"

# Cor que o Windows torna transparente: precisa ser uma que nunca apareca no
# desenho real, senao buracos aparecem no widget.
CHROMA = "#ff00fe"

PAD = 14
WIDTH = 292
RING_SIZE = 62

MODES = ("mini", "summary", "full")


def level_color(pct: float) -> str:
    if pct >= 85:
        return CRIT
    if pct >= 60:
        return WARN
    return OK


def fmt_tokens(value: int) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B".replace(".", ",")
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M".replace(".", ",")
    if value >= 1_000:
        return f"{value / 1_000:.0f}k"
    return str(value)


def fmt_money(value: float) -> str:
    return f"${value:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def fmt_duration(seconds: int) -> str:
    """Duracao curta em portugues: '2h05', '17 min', 'agora'."""
    if seconds <= 0:
        return "agora"
    minutes = seconds // 60
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}"
    return f"{minutes} min"


class Ring(tk.Canvas):
    """Circulo do modo mini: anel de progresso com o percentual no centro."""

    def __init__(self, parent, size: int = RING_SIZE) -> None:
        super().__init__(
            parent, width=size, height=size, bg=CHROMA,
            highlightthickness=0, bd=0,
        )
        self.size = size
        pad = 4
        box = (pad, pad, size - pad, size - pad)

        # Disco de fundo, para o texto ter contraste sobre qualquer janela.
        self.create_oval(1, 1, size - 1, size - 1, fill=BG, outline=BORDER)
        self._track = self.create_arc(
            *box, start=90, extent=-359.9, style="arc", width=4, outline=TRACK
        )
        self._arc = self.create_arc(
            *box, start=90, extent=0, style="arc", width=4, outline=OK
        )
        self._value = self.create_text(
            size / 2, size / 2 - 4, text="--", fill=FG,
            font=("Segoe UI", 12, "bold"),
        )
        self._caption = self.create_text(
            size / 2, size / 2 + 11, text="5h", fill=FG_FAINT,
            font=("Segoe UI", 6),
        )

    def set(self, pct: float | None, caption: str = "5h", estimated: bool = False) -> None:
        if pct is None:
            self.itemconfigure(self._arc, extent=0)
            self.itemconfigure(self._value, text="--", fill=FG_FAINT)
        else:
            pct = min(max(pct, 0.0), 100.0)
            color = level_color(pct)
            # -0.1 evita o arco completo virar circulo fechado sem inicio visivel.
            self.itemconfigure(
                self._arc, extent=-(pct * 3.599 or 0.1), outline=color
            )
            prefix = "~" if estimated else ""
            self.itemconfigure(self._value, text=f"{prefix}{pct:.0f}%", fill=color)
        self.itemconfigure(self._caption, text=caption)


class Bar(tk.Canvas):
    """Barra de progresso fina, redesenhada quando a largura muda."""

    HEIGHT = 6

    def __init__(self, parent) -> None:
        # A largura inicial importa: sem ela o Canvas assume o padrao do tkinter
        # (378px) e estica o painel inteiro. O <Configure> cuida do resto.
        super().__init__(
            parent, height=self.HEIGHT, width=WIDTH - PAD * 2,
            bg=BG, highlightthickness=0, bd=0,
        )
        self._pct = 0.0
        self._color = OK
        self._track = self.create_rectangle(0, 0, 0, self.HEIGHT, fill=TRACK, outline="")
        self._fill = self.create_rectangle(0, 0, 0, self.HEIGHT, fill=OK, outline="")
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
        super().__init__(parent, bg=BG)
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x")

        tk.Label(
            head, text=title, bg=BG, fg=FG_DIM, anchor="w",
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")

        self.value = tk.Label(
            head, text="--", bg=BG, fg=FG, anchor="e",
            font=("Segoe UI", 12, "bold"),
        )
        self.value.pack(side="right")

        self.bar = Bar(self)
        self.bar.pack(fill="x", pady=(3, 3))

        # wraplength impede que uma legenda longa estique a largura do painel.
        self.caption = tk.Label(
            self, text="", bg=BG, fg=FG_FAINT, anchor="w", justify="left",
            font=("Segoe UI", 8), wraplength=WIDTH - PAD * 2,
        )
        self.caption.pack(fill="x")

    def update_values(self, pct: float | None, caption: str, estimated: bool = False) -> None:
        if pct is None:
            self.value.configure(text="--", fg=FG_FAINT)
            self.bar.set(0)
        else:
            color = level_color(pct)
            prefix = "~" if estimated else ""
            self.value.configure(text=f"{prefix}{pct:.0f}%", fg=color)
            self.bar.set(pct, color)
        self.caption.configure(text=caption)


class UsageWidget(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.cfg = Config.load()
        self.tz = local_timezone()
        self.collector = Collector(history_days=self.cfg.history_days)
        self.live = LiveState()
        self.mode = self.cfg.mode if self.cfg.mode in MODES else "summary"
        self._loading = True
        self._drag = (0, 0)
        self._session_pct: float | None = None
        self._session_estimated = False

        self._setup_window()
        self._build()
        self._apply_mode(self.mode, save=False)
        self.after(60, self._kick_refresh)

    # ------------------------------------------------------------- estrutura

    def _setup_window(self) -> None:
        self.title("Uso do Claude Code")
        self.overrideredirect(True)  # sem barra de titulo do sistema
        self.configure(bg=BG)
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
        self.panel = tk.Frame(self.container, bg=BORDER)
        root = tk.Frame(self.panel, bg=BG)
        root.pack(fill="both", expand=True, padx=1, pady=1)
        self.panel_root = root
        # Espacador de altura zero: fixa a largura do painel sem impedir que o
        # frame calcule a propria altura a partir dos filhos.
        tk.Frame(root, bg=BG, width=WIDTH, height=0).pack()

        # ---- cabecalho
        header = tk.Frame(root, bg=BG_SOFT, height=30)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.header = header

        self.dot = tk.Label(header, text="◆", bg=BG_SOFT, fg=ACCENT, font=("Segoe UI", 9))
        self.dot.pack(side="left", padx=(PAD - 2, 5))
        self.heading = tk.Label(
            header, text="CLAUDE CODE", bg=BG_SOFT, fg=FG, font=("Segoe UI", 8, "bold")
        )
        self.heading.pack(side="left")

        self._header_button(header, "✕", self.quit_widget, CRIT, pad=(4, PAD - 5))
        self._header_button(header, "⋮", self._show_menu_at_button, ACCENT)
        self._header_button(header, "–", lambda: self._apply_mode("mini"), ACCENT)

        self.source_badge = tk.Label(
            header, text="", bg=BG_SOFT, fg=FG_FAINT, font=("Segoe UI", 7)
        )
        self.source_badge.pack(side="right", padx=(0, 8))

        # ---- corpo
        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=PAD, pady=(12, 4))

        self.session_meter = Meter(body, "SESSÃO ATUAL")
        self.session_meter.pack(fill="x")

        self.week_meter = Meter(body, "SEMANA")
        self.week_meter.pack(fill="x", pady=(12, 0))

        # ---- blocos exclusivos do modo completo
        self.full_only = tk.Frame(body, bg=BG)

        tk.Frame(self.full_only, bg=BORDER, height=1).pack(fill="x", pady=(13, 10))

        stats = tk.Frame(self.full_only, bg=BG)
        stats.pack(fill="x")
        self.tokens_label = self._stat(stats, "left", "tokens")
        self.cost_label = self._stat(stats, "right", "valor estimado")

        self.projects_frame = tk.Frame(self.full_only, bg=BG)

        self.footer = tk.Label(
            root, text="carregando…", bg=BG, fg=FG_FAINT, anchor="w",
            justify="left", font=("Segoe UI", 7), wraplength=WIDTH - PAD * 2,
        )

        for widget in (header, self.dot, self.heading):
            widget.bind("<Button-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_move)
            widget.bind("<ButtonRelease-1>", self._drag_end)
            widget.bind("<Double-Button-1>", lambda _e: self._toggle_detail())

        self.panel.bind("<Button-3>", self._show_menu)
        root.bind("<Button-3>", self._show_menu)
        self.bind("<Escape>", lambda _e: self.quit_widget())

    def _header_button(self, parent, text, command, hover, pad=(4, 2)):
        btn = tk.Label(
            parent, text=text, bg=BG_SOFT, fg=FG_FAINT,
            font=("Segoe UI", 10), cursor="hand2",
        )
        btn.pack(side="right", padx=pad)
        btn.bind("<Button-1>", lambda e: command(e) if _wants_event(command) else command())
        btn.bind("<Enter>", lambda _e: btn.configure(fg=hover))
        btn.bind("<Leave>", lambda _e: btn.configure(fg=FG_FAINT))
        return btn

    def _stat(self, parent, side: str, caption: str):
        holder = tk.Frame(parent, bg=BG)
        holder.pack(side=side)
        anchor = "w" if side == "left" else "e"
        value = tk.Label(
            holder, text="--", bg=BG, fg=FG, anchor=anchor, font=("Segoe UI", 13, "bold")
        )
        value.pack(anchor=anchor)
        tk.Label(
            holder, text=caption, bg=BG, fg=FG_FAINT, anchor=anchor, font=("Segoe UI", 7)
        ).pack(anchor=anchor)
        return value

    def _build_menu(self) -> None:
        self.menu = tk.Menu(
            self, tearoff=0, bg=BG_SOFT, fg=FG, activebackground=ACCENT,
            activeforeground="#1a1613", bd=0, font=("Segoe UI", 9),
        )
        self.var_mode = tk.StringVar(value=self.mode)
        self.var_top = tk.BooleanVar(value=self.cfg.always_on_top)
        self.var_projects = tk.BooleanVar(value=self.cfg.show_projects)

        for label, value in (
            ("Minimizado", "mini"),
            ("Resumo", "summary"),
            ("Completo", "full"),
        ):
            self.menu.add_radiobutton(
                label=label, value=value, variable=self.var_mode,
                command=lambda v=value: self._apply_mode(v),
            )
        self.menu.add_separator()
        self.menu.add_command(label="Atualizar agora", command=self._kick_refresh)
        self.menu.add_checkbutton(
            label="Sempre visível", variable=self.var_top, command=self._toggle_top
        )
        self.menu.add_checkbutton(
            label="Mostrar projetos", variable=self.var_projects,
            command=self._toggle_projects,
        )
        opacity = tk.Menu(
            self.menu, tearoff=0, bg=BG_SOFT, fg=FG,
            activebackground=ACCENT, activeforeground="#1a1613",
        )
        for label, value in (("100%", 1.0), ("96%", 0.96), ("85%", 0.85), ("70%", 0.70)):
            opacity.add_command(label=label, command=lambda v=value: self._set_opacity(v))
        self.menu.add_cascade(label="Opacidade", menu=opacity)
        self.menu.add_separator()
        self.menu.add_command(label="Fechar", command=self.quit_widget)

    # ------------------------------------------------------------------ modos

    def _apply_mode(self, mode: str, save: bool = True) -> None:
        if mode not in MODES:
            mode = "summary"
        self.mode = mode
        self.var_mode.set(mode)

        self.ring_holder.pack_forget()
        self.panel.pack_forget()
        self.full_only.pack_forget()
        self.footer.pack_forget()

        if mode == "mini":
            self.container.configure(bg=CHROMA)
            self.ring_holder.pack()
        else:
            self.container.configure(bg=BG)
            self.panel.pack(fill="both", expand=True)
            if mode == "full":
                self.full_only.pack(fill="x")
                self.footer.pack(fill="x", padx=PAD, pady=(8, 7))
            else:
                self.footer.pack(fill="x", padx=PAD, pady=(10, 8))

        self._resize()
        if save:
            self.cfg.mode = mode
            self.cfg.save()
        self._render()

    def _resize(self) -> None:
        """Reajusta a janela ao conteudo do modo atual.

        `geometry("")` devolve o dimensionamento ao tkinter, que mede o
        conteudo visivel; a posicao atual e preservada.
        """
        self.update_idletasks()
        self.geometry("")
        self.update_idletasks()

    def _toggle_detail(self) -> None:
        self._apply_mode("full" if self.mode == "summary" else "summary")

    def _cycle_mode(self) -> None:
        self._apply_mode(MODES[(MODES.index(self.mode) + 1) % len(MODES)])

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
        """Clique sem arrastar abre o resumo; arrastar so reposiciona."""
        origin = getattr(self, "_drag_origin", (event.x_root, event.y_root))
        moved = abs(event.x_root - origin[0]) + abs(event.y_root - origin[1])
        self._drag_end()
        if moved < 5:
            self._apply_mode("summary")

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

    def _toggle_top(self) -> None:
        self.cfg.always_on_top = self.var_top.get()
        self.attributes("-topmost", self.cfg.always_on_top)
        self.cfg.save()

    def _toggle_projects(self) -> None:
        self.cfg.show_projects = self.var_projects.get()
        self.cfg.save()
        self._render()
        self._resize()

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

    def _kick_refresh(self, _event=None) -> None:
        """Dispara a coleta numa thread, para a interface nunca congelar."""
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            self.collector.refresh()
            self.collector.prune()
            self.live = read_state()
        except Exception:  # o widget nunca deve morrer por causa de um refresh
            pass
        self._loading = False
        try:
            self.after(0, self._render)
            self.after(self.cfg.refresh_seconds * 1000, self._kick_refresh)
        except RuntimeError:
            pass  # janela ja fechada

    def _render(self) -> None:
        now = datetime.now(timezone.utc)
        self._render_session(now)
        self._render_week()
        if self.mode == "mini":
            self.ring.set(self._session_pct, "5h", self._session_estimated)
            return
        if self.mode == "full":
            self._render_details(now)
        self._render_footer()

    def _render_session(self, now) -> None:
        official = self.live.five_hour
        if official is not None and official.expired:
            official = None

        if official is not None:
            self._session_pct = official.used_percentage
            self._session_estimated = False
            remaining = fmt_duration(official.remaining_seconds())
            caption = f"Reinicia em {remaining}"
            if official.resets_at:
                clock = datetime.fromtimestamp(official.resets_at, tz=self.tz)
                caption += f" · {clock:%H:%M}"
            self.session_meter.update_values(official.used_percentage, caption)
            return

        block = current_block(
            self.collector.requests, now=now, anchor=self.cfg.block_anchor_dt()
        )
        if block is not None:
            # Sem numero oficial mostramos o tempo decorrido da janela, que e
            # verificavel, em vez de inventar um percentual de consumo.
            elapsed = block.elapsed_fraction(now) * 100
            self._session_pct = elapsed
            self._session_estimated = True
            remaining = fmt_duration(int(block.remaining(now).total_seconds()))
            reset_local = block.end.astimezone(self.tz)
            self.session_meter.update_values(
                elapsed,
                f"~Reinicia em {remaining} · {reset_local:%H:%M} · tempo decorrido",
                estimated=True,
            )
        else:
            self._session_pct = None
            self._session_estimated = False
            self.session_meter.update_values(None, "Nenhuma sessão ativa")

    def _render_week(self) -> None:
        week = self.live.seven_day
        if week is not None and week.expired:
            week = None

        if week is None:
            self.week_meter.update_values(None, "Instale a status line para o %")
            return

        caption = "Todos os modelos"
        if week.resets_at:
            clock = datetime.fromtimestamp(week.resets_at, tz=self.tz)
            dias = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
            caption = (
                f"Reinicia {dias[clock.weekday()]} {clock:%d/%m} · {clock:%H:%M}"
            )
        self.week_meter.update_values(week.used_percentage, caption)

    def _render_details(self, now) -> None:
        block = current_block(
            self.collector.requests, now=now, anchor=self.cfg.block_anchor_dt()
        )
        if block is not None:
            self.tokens_label.configure(text=fmt_tokens(block.totals.total_tokens))
            self.cost_label.configure(text=fmt_money(block.totals.cost))
        else:
            self.tokens_label.configure(text="--")
            self.cost_label.configure(text="--")
        self._render_projects(now)

    def _render_projects(self, now) -> None:
        for row in self.projects_frame.winfo_children():
            row.destroy()

        if not self.cfg.show_projects:
            self.projects_frame.pack_forget()
            return

        start, end = week_period(self.cfg.weekly_anchor_dt(), now)
        if self.live.seven_day and self.live.seven_day.resets_at:
            # Alinha a lista ao periodo semanal oficial, quando ele e conhecido.
            end = datetime.fromtimestamp(self.live.seven_day.resets_at, tz=timezone.utc)
            start = end - timedelta(days=7)

        top = group_by(self.collector.requests, "project", start, end, limit=3)
        if not top:
            self.projects_frame.pack_forget()
            return

        self.projects_frame.pack(fill="x", pady=(12, 0))
        tk.Label(
            self.projects_frame, text="PROJETOS · SEMANA", bg=BG, fg=FG_FAINT,
            anchor="w", font=("Segoe UI", 7, "bold"),
        ).pack(fill="x", pady=(0, 5))

        peak = max((t.cost for _, t in top), default=0.0) or 1.0
        share_width = 44
        for name, totals in top:
            row = tk.Frame(self.projects_frame, bg=BG)
            row.pack(fill="x", pady=1)
            tk.Label(
                row, text=name[:20], bg=BG, fg=FG_DIM, anchor="w", font=("Segoe UI", 8)
            ).pack(side="left")
            tk.Label(
                row, text=fmt_money(totals.cost), bg=BG, fg=FG_DIM, anchor="e",
                font=("Segoe UI", 8), width=9,
            ).pack(side="right")
            # Barra proporcional ao maior da lista, so como apoio de leitura.
            share = tk.Canvas(
                row, height=3, width=share_width, bg=BG, highlightthickness=0, bd=0
            )
            share.pack(side="right", padx=(6, 4))
            filled = max(int(share_width * totals.cost / peak), 2)
            share.create_rectangle(
                share_width - filled, 0, share_width, 3, fill=BORDER, outline=""
            )

    def _render_footer(self) -> None:
        if self._loading:
            self.footer.configure(text="carregando…")
            return

        if self.live.available and not self.live.stale:
            self.source_badge.configure(text="oficial", fg=OK)
            age = int(self.live.age_seconds)
            origem = "sincronizado agora" if age < 60 else f"sincronizado há {fmt_duration(age)}"
        elif self.live.available:
            self.source_badge.configure(text="cache", fg=WARN)
            origem = f"status line parada há {fmt_duration(int(self.live.age_seconds))}"
        else:
            self.source_badge.configure(text="local", fg=FG_FAINT)
            origem = "estimado dos logs locais"

        self.footer.configure(text=f"{origem} · {self.live.model or '-'}")


def _wants_event(func) -> bool:
    """Callbacks de botao recebem o evento so quando declaram um parametro."""
    try:
        from inspect import signature

        return len(signature(func).parameters) >= 1
    except (TypeError, ValueError):
        return False


def run() -> None:
    UsageWidget().mainloop()
