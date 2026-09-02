"""Widget flutuante de uso do Claude Code.

Janela sem bordas, sempre no topo e arrastavel, montada com tkinter (biblioteca
padrao -- nao ha dependencias para instalar).

Duas fontes alimentam a tela:

* **Oficial** -- percentuais e horarios de reset publicados pela ponte de
  status line (`ccwidget.statusline`). Sao os mesmos numeros do `/usage`.
* **Local** -- tokens, custo equivalente e projetos, calculados a partir dos
  logs de sessao. Aparecem sempre, e viram fallback quando o oficial falta.

Tudo que e estimado leva o prefixo `~` na interface, para nao se confundir com
o dado oficial.
"""

from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime, timedelta, timezone

from .analytics import current_block, group_by, totals_between, week_period
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

PAD = 14
WIDTH = 296


def level_color(pct: float) -> str:
    if pct >= 85:
        return CRIT
    if pct >= 60:
        return WARN
    return OK


def fmt_tokens(value: int) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}k"
    return str(value)


def fmt_duration(seconds: int) -> str:
    if seconds <= 0:
        return "now"
    hours, minutes = divmod(seconds // 60, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    return f"{minutes}m"


class Bar(tk.Canvas):
    """Barra de progresso fina, desenhada a mao para nao herdar o visual do ttk."""

    HEIGHT = 6

    def __init__(self, parent, width: int = WIDTH - PAD * 2) -> None:
        super().__init__(
            parent,
            width=width,
            height=self.HEIGHT,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )
        self._width = width
        self._track = self.create_rectangle(
            0, 0, width, self.HEIGHT, fill=TRACK, outline=""
        )
        self._fill = self.create_rectangle(0, 0, 0, self.HEIGHT, fill=OK, outline="")

    def set(self, pct: float, color: str | None = None) -> None:
        pct = min(max(pct, 0.0), 100.0)
        filled = max(int(self._width * pct / 100), 2 if pct > 0 else 0)
        self.coords(self._fill, 0, 0, filled, self.HEIGHT)
        self.itemconfigure(self._fill, fill=color or level_color(pct))


class Meter(tk.Frame):
    """Rotulo + valor + barra + legenda: o bloco visual de uma janela de limite."""

    def __init__(self, parent, title: str) -> None:
        super().__init__(parent, bg=BG)
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x")

        self.title = tk.Label(
            head, text=title, bg=BG, fg=FG_DIM, anchor="w",
            font=("Segoe UI", 8, "bold"),
        )
        self.title.pack(side="left")

        self.value = tk.Label(
            head, text="--", bg=BG, fg=FG, anchor="e",
            font=("Segoe UI", 11, "bold"),
        )
        self.value.pack(side="right")

        self.bar = Bar(self)
        self.bar.pack(fill="x", pady=(3, 2))

        self.caption = tk.Label(
            self, text="", bg=BG, fg=FG_FAINT, anchor="w",
            font=("Segoe UI", 8),
        )
        self.caption.pack(fill="x")

    def update_values(
        self, pct: float | None, caption: str, estimated: bool = False
    ) -> None:
        if pct is None:
            self.value.configure(text="--", fg=FG_FAINT)
            self.bar.set(0)
        else:
            prefix = "~" if estimated else ""
            color = level_color(pct)
            self.value.configure(text=f"{prefix}{pct:.0f}%", fg=color)
            self.bar.set(pct, color)
        self.caption.configure(text=caption)


class UsageWidget(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.config_data = Config.load()
        self.tz = local_timezone()
        self.collector = Collector(history_days=self.config_data.history_days)
        self.live = LiveState()
        self._loading = True
        self._drag = (0, 0)

        self._setup_window()
        self._build()
        self._bind_events()

        self.after(60, self._kick_refresh)

    # ------------------------------------------------------------- estrutura

    def _setup_window(self) -> None:
        self.title("Claude Code Usage")
        self.overrideredirect(True)  # sem barra de titulo do sistema
        self.configure(bg=BG)
        self.attributes("-topmost", self.config_data.always_on_top)
        try:
            self.attributes("-alpha", self.config_data.opacity)
        except tk.TclError:
            pass
        self.geometry(f"+{self.config_data.pos_x}+{self.config_data.pos_y}")

    def _build(self) -> None:
        # Borda de 1px: um frame externo colorido com o conteudo por dentro.
        outer = tk.Frame(self, bg=BORDER)
        outer.pack(fill="both", expand=True)
        root = tk.Frame(outer, bg=BG)
        root.pack(fill="both", expand=True, padx=1, pady=1)

        # ---- cabecalho
        header = tk.Frame(root, bg=BG_SOFT, height=30)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.header = header

        self.dot = tk.Label(
            header, text="◆", bg=BG_SOFT, fg=ACCENT, font=("Segoe UI", 9)
        )
        self.dot.pack(side="left", padx=(PAD - 2, 5))

        self.heading = tk.Label(
            header, text="CLAUDE CODE", bg=BG_SOFT, fg=FG,
            font=("Segoe UI", 8, "bold"),
        )
        self.heading.pack(side="left")

        close = tk.Label(
            header, text="✕", bg=BG_SOFT, fg=FG_FAINT,
            font=("Segoe UI", 9), cursor="hand2",
        )
        close.pack(side="right", padx=(4, PAD - 4))
        close.bind("<Button-1>", lambda _e: self.quit_widget())
        close.bind("<Enter>", lambda _e: close.configure(fg=CRIT))
        close.bind("<Leave>", lambda _e: close.configure(fg=FG_FAINT))

        self.source_badge = tk.Label(
            header, text="", bg=BG_SOFT, fg=FG_FAINT, font=("Segoe UI", 7)
        )
        self.source_badge.pack(side="right", padx=(0, 6))

        # ---- corpo
        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=PAD, pady=(12, 10))
        self.body = body

        self.session_meter = Meter(body, "SESSION · 5H")
        self.session_meter.pack(fill="x")

        self.week_meter = Meter(body, "WEEK")
        self.week_meter.pack(fill="x", pady=(12, 0))

        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(12, 9))

        # ---- metricas locais
        stats = tk.Frame(body, bg=BG)
        stats.pack(fill="x")
        self.tokens_label = self._stat(stats, "left", "--", "tokens")
        self.cost_label = self._stat(stats, "right", "--", "est. value")

        # ---- projetos
        self.projects_frame = tk.Frame(body, bg=BG)
        self.project_rows: list[tuple[tk.Label, tk.Label]] = []

        # ---- rodape
        self.footer = tk.Label(
            root, text="loading…", bg=BG, fg=FG_FAINT, anchor="w",
            font=("Segoe UI", 7),
        )
        self.footer.pack(fill="x", padx=PAD, pady=(0, 8))

        self._build_menu()

    def _stat(self, parent, side: str, value: str, caption: str):
        holder = tk.Frame(parent, bg=BG)
        holder.pack(side=side)
        anchor = "w" if side == "left" else "e"
        val = tk.Label(
            holder, text=value, bg=BG, fg=FG, anchor=anchor,
            font=("Segoe UI", 13, "bold"),
        )
        val.pack(anchor=anchor)
        cap = tk.Label(
            holder, text=caption, bg=BG, fg=FG_FAINT, anchor=anchor,
            font=("Segoe UI", 7),
        )
        cap.pack(anchor=anchor)
        return val

    def _build_menu(self) -> None:
        self.menu = tk.Menu(
            self, tearoff=0, bg=BG_SOFT, fg=FG,
            activebackground=ACCENT, activeforeground="#1a1613",
            bd=0, font=("Segoe UI", 9),
        )
        self.var_top = tk.BooleanVar(value=self.config_data.always_on_top)
        self.var_projects = tk.BooleanVar(value=self.config_data.show_projects)

        self.menu.add_command(label="Refresh now", command=self._kick_refresh)
        self.menu.add_separator()
        self.menu.add_checkbutton(
            label="Always on top", variable=self.var_top, command=self._toggle_top
        )
        self.menu.add_checkbutton(
            label="Show projects", variable=self.var_projects,
            command=self._toggle_projects,
        )
        opacity_menu = tk.Menu(self.menu, tearoff=0, bg=BG_SOFT, fg=FG,
                               activebackground=ACCENT, activeforeground="#1a1613")
        for label, value in (("100%", 1.0), ("94%", 0.94), ("85%", 0.85), ("70%", 0.7)):
            opacity_menu.add_command(
                label=label, command=lambda v=value: self._set_opacity(v)
            )
        self.menu.add_cascade(label="Opacity", menu=opacity_menu)
        self.menu.add_separator()
        self.menu.add_command(label="Quit", command=self.quit_widget)

    def _bind_events(self) -> None:
        for widget in (self.header, self.dot, self.heading):
            widget.bind("<Button-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_move)
            widget.bind("<ButtonRelease-1>", self._drag_end)
        self.bind("<Button-3>", self._show_menu)
        self.bind("<Double-Button-1>", lambda _e: self._kick_refresh())
        self.bind("<Escape>", lambda _e: self.quit_widget())

    # ---------------------------------------------------------- interacoes

    def _drag_start(self, event) -> None:
        self._drag = (event.x_root - self.winfo_x(), event.y_root - self.winfo_y())

    def _drag_move(self, event) -> None:
        x = event.x_root - self._drag[0]
        y = event.y_root - self._drag[1]
        self.geometry(f"+{x}+{y}")

    def _drag_end(self, _event) -> None:
        self.config_data.pos_x = self.winfo_x()
        self.config_data.pos_y = self.winfo_y()
        self.config_data.save()

    def _show_menu(self, event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _toggle_top(self) -> None:
        self.config_data.always_on_top = self.var_top.get()
        self.attributes("-topmost", self.config_data.always_on_top)
        self.config_data.save()

    def _toggle_projects(self) -> None:
        self.config_data.show_projects = self.var_projects.get()
        self.config_data.save()
        self._render()

    def _set_opacity(self, value: float) -> None:
        self.config_data.opacity = value
        try:
            self.attributes("-alpha", value)
        except tk.TclError:
            pass
        self.config_data.save()

    def quit_widget(self) -> None:
        self.config_data.pos_x = self.winfo_x()
        self.config_data.pos_y = self.winfo_y()
        self.config_data.save()
        self.destroy()

    # ------------------------------------------------------------ atualizacao

    def _kick_refresh(self) -> None:
        """Dispara a coleta numa thread, para a interface nunca congelar."""
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            self.collector.refresh()
            self.collector.prune()
            live = read_state()
        except Exception:  # o widget nunca deve morrer por causa de um refresh
            live = self.live
        self.live = live
        self._loading = False
        try:
            self.after(0, self._render)
            self.after(self.config_data.refresh_seconds * 1000, self._kick_refresh)
        except RuntimeError:
            pass  # janela ja fechada

    def _render(self) -> None:
        now = datetime.now(timezone.utc)
        requests = self.collector.requests

        block = current_block(requests, now=now, anchor=self.config_data.block_anchor_dt())
        official = self.live.five_hour if self.live.five_hour and not self.live.five_hour.expired else None

        # ---- sessao de 5 horas
        if official is not None:
            reset_at = datetime.fromtimestamp(official.resets_at, tz=self.tz) if official.resets_at else None
            caption = "resets --"
            if reset_at:
                caption = (
                    f"resets {reset_at.strftime('%H:%M')}"
                    f" · in {fmt_duration(official.remaining_seconds())}"
                )
            self.session_meter.update_values(official.used_percentage, caption)
        elif block is not None:
            # Sem numero oficial: mostra o tempo decorrido da janela, que e
            # verificavel, em vez de inventar um percentual de consumo.
            elapsed = block.elapsed_fraction(now) * 100
            reset_local = block.end.astimezone(self.tz)
            caption = (
                f"~resets {reset_local.strftime('%H:%M')}"
                f" · window elapsed"
            )
            self.session_meter.update_values(elapsed, caption, estimated=True)
        else:
            self.session_meter.update_values(None, "no active session")

        # ---- semana
        week_official = self.live.seven_day if self.live.seven_day and not self.live.seven_day.expired else None
        if week_official is not None:
            reset_at = (
                datetime.fromtimestamp(week_official.resets_at, tz=self.tz)
                if week_official.resets_at
                else None
            )
            caption = (
                f"resets {reset_at.strftime('%a %d/%m %H:%M')}" if reset_at else "all models"
            )
            self.week_meter.update_values(week_official.used_percentage, caption)
        else:
            self.week_meter.update_values(None, "install status line for %")

        # ---- metricas locais do bloco
        if block is not None:
            self.tokens_label.configure(text=fmt_tokens(block.totals.total_tokens))
            self.cost_label.configure(text=f"${block.totals.cost:,.2f}")
        else:
            self.tokens_label.configure(text="--")
            self.cost_label.configure(text="--")

        self._render_projects(now)
        self._render_footer()

    def _render_projects(self, now) -> None:
        for row in self.projects_frame.winfo_children():
            row.destroy()

        if not self.config_data.show_projects:
            self.projects_frame.pack_forget()
            return

        start, end = week_period(self.config_data.weekly_anchor_dt(), now)
        if self.live.seven_day and self.live.seven_day.resets_at:
            # Alinha a lista ao periodo semanal oficial, quando ele e conhecido.
            end = datetime.fromtimestamp(self.live.seven_day.resets_at, tz=timezone.utc)
            start = end - timedelta(days=7)

        top = group_by(self.collector.requests, "project", start, end, limit=3)
        if not top:
            self.projects_frame.pack_forget()
            return

        self.projects_frame.pack(fill="x", pady=(10, 0))
        header = tk.Label(
            self.projects_frame, text="TOP PROJECTS · WEEK", bg=BG, fg=FG_FAINT,
            anchor="w", font=("Segoe UI", 7, "bold"),
        )
        header.pack(fill="x", pady=(0, 4))

        peak = max((t.cost for _, t in top), default=0.0) or 1.0
        share_width = 46
        for name, totals in top:
            row = tk.Frame(self.projects_frame, bg=BG)
            row.pack(fill="x", pady=1)
            tk.Label(
                row, text=name[:20], bg=BG, fg=FG_DIM, anchor="w",
                font=("Segoe UI", 8),
            ).pack(side="left")
            tk.Label(
                row, text=f"${totals.cost:,.2f}", bg=BG, fg=FG_DIM, anchor="e",
                font=("Segoe UI", 8), width=8,
            ).pack(side="right")
            # Barra proporcional ao maior projeto da lista, so como apoio visual.
            share = tk.Canvas(
                row, height=3, width=share_width, bg=BG,
                highlightthickness=0, bd=0,
            )
            share.pack(side="right", padx=(6, 4))
            filled = max(int(share_width * totals.cost / peak), 2)
            share.create_rectangle(
                share_width - filled, 0, share_width, 3, fill=BORDER, outline=""
            )

    def _render_footer(self) -> None:
        if self._loading:
            self.footer.configure(text="loading…")
            return

        if self.live.available and not self.live.stale:
            age = int(self.live.age_seconds)
            self.source_badge.configure(text="official", fg=OK)
            source = f"synced {fmt_duration(age) if age > 60 else 'just now'}"
        elif self.live.available:
            self.source_badge.configure(text="cached", fg=WARN)
            source = f"status line idle for {fmt_duration(int(self.live.age_seconds))}"
        else:
            self.source_badge.configure(text="local", fg=FG_FAINT)
            source = "estimated from local logs"

        model = self.live.model or "-"
        self.footer.configure(text=f"{source} · {model}")


def run() -> None:
    widget = UsageWidget()
    widget.mainloop()
