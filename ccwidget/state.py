"""Leitura do estado publicado pela ponte de status line.

Este e o unico caminho para os numeros *oficiais* de limite. Quando o arquivo
nao existe (status line nao instalada) ou esta velho demais, o widget cai para
a estimativa calculada a partir dos logs locais.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

STATE_PATH = Path.home() / ".ccwidget" / "state.json"

# Acima disso o estado e considerado velho: nenhuma sessao do Claude Code
# renderizou a status line recentemente.
STALE_AFTER_SECONDS = 15 * 60


@dataclass(slots=True)
class Window:
    """Uma janela de limite (5 horas ou 7 dias) com dados oficiais."""

    used_percentage: float
    resets_at: float | None = None

    @property
    def expired(self) -> bool:
        return self.resets_at is not None and self.resets_at <= time.time()

    def remaining_seconds(self) -> int:
        if not self.resets_at:
            return 0
        return max(int(self.resets_at - time.time()), 0)


@dataclass(slots=True)
class LiveState:
    """Estado publicado pela status line do Claude Code."""

    updated_at: float = 0.0
    model: str | None = None
    session_cost: float | None = None
    context_used_percentage: float | None = None
    five_hour: Window | None = None
    seven_day: Window | None = None
    spend_limit: Window | None = None

    @property
    def age_seconds(self) -> float:
        return time.time() - self.updated_at if self.updated_at else float("inf")

    @property
    def stale(self) -> bool:
        return self.age_seconds > STALE_AFTER_SECONDS

    @property
    def available(self) -> bool:
        """Ha ao menos uma janela oficial valida?"""
        return any(
            w is not None and not w.expired
            for w in (self.five_hour, self.seven_day)
        )


def _window(data: dict | None) -> Window | None:
    if not isinstance(data, dict):
        return None
    pct = data.get("used_percentage")
    if pct is None:
        return None
    try:
        return Window(used_percentage=float(pct), resets_at=data.get("resets_at"))
    except (TypeError, ValueError):
        return None


def read_state(path: Path | None = None) -> LiveState:
    """Le o estado do disco. Nunca levanta excecao: sem arquivo, devolve vazio."""
    target = path or STATE_PATH
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return LiveState()
    if not isinstance(raw, dict):
        return LiveState()

    limits = raw.get("rate_limits") or {}
    cost = raw.get("cost") or {}
    ctx = raw.get("context_window") or {}

    return LiveState(
        updated_at=float(raw.get("updated_at") or 0.0),
        model=raw.get("model"),
        session_cost=cost.get("total_cost_usd"),
        context_used_percentage=ctx.get("used_percentage"),
        five_hour=_window(limits.get("five_hour")),
        seven_day=_window(limits.get("seven_day")),
        spend_limit=_window(limits.get("spend_limit")),
    )
