"""Configuracao persistente do widget.

Guardada em ~/.ccwidget/config.json. Todos os campos tem padrao razoavel: o
widget funciona sem nenhuma configuracao previa.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

CONFIG_DIR = Path.home() / ".ccwidget"
CONFIG_PATH = CONFIG_DIR / "config.json"


def local_timezone():
    """Fuso horario local do sistema."""
    return datetime.now().astimezone().tzinfo


@dataclass
class Config:
    # --- atualizacao -------------------------------------------------------
    refresh_seconds: int = 20
    history_days: int = 30

    # --- limites de referencia --------------------------------------------
    # O Claude Code nao expoe localmente o denominador dos limites; estes
    # valores sao calibrados pelo usuario a partir do que o /usage mostra.
    # Unidade: custo equivalente em USD (pondera modelos caros corretamente).
    session_limit_cost: float | None = None
    weekly_limit_cost: float | None = None

    # --- ancoras de janela -------------------------------------------------
    # ISO 8601. `block_anchor` e o inicio do bloco de 5h; `weekly_anchor` e
    # qualquer instante de reset semanal conhecido.
    block_anchor: str | None = None
    weekly_anchor: str | None = None

    # --- janela ------------------------------------------------------------
    pos_x: int = 40
    pos_y: int = 40
    opacity: float = 0.94
    always_on_top: bool = True
    show_projects: bool = True
    show_models: bool = False

    # ---------------------------------------------------------------- infra

    @classmethod
    def load(cls) -> "Config":
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self) -> None:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(
                json.dumps(asdict(self), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass  # config e conveniencia; nunca derruba o widget

    # ------------------------------------------------------------- ancoras

    def block_anchor_dt(self) -> datetime | None:
        return _parse_iso(self.block_anchor)

    def weekly_anchor_dt(self) -> datetime | None:
        return _parse_iso(self.weekly_anchor)

    def set_block_reset(self, reset_local: datetime) -> None:
        """Define a ancora do bloco a partir do horario de reset do /usage."""
        from .analytics import BLOCK_HOURS
        from datetime import timedelta

        start = reset_local.astimezone(timezone.utc) - timedelta(hours=BLOCK_HOURS)
        self.block_anchor = start.isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=local_timezone())
    return dt.astimezone(timezone.utc)
