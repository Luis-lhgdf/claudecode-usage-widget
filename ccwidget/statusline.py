"""Ponte entre o Claude Code e o widget.

O Claude Code envia um JSON no stdin do comando configurado em `statusLine`,
e esse JSON traz os unicos numeros *oficiais* de limite disponiveis fora da
interface: `rate_limits.five_hour` e `rate_limits.seven_day`, cada um com
`used_percentage` e `resets_at`.

Este script faz duas coisas a cada renderizacao:

1. Grava o estado em ~/.ccwidget/state.json, de onde o widget le.
2. Imprime uma status line enxuta, para a linha do terminal nao ser desperdicada.

Precisa ser rapido: roda a cada atualizacao da interface. Por isso importa
apenas a biblioteca padrao e nao carrega o resto do pacote.

Ressalvas da documentacao do Claude Code:
- `rate_limits` so aparece para assinantes Claude.ai Pro e Max (ou atras de um
  gateway com limite de gasto) e apenas depois da primeira resposta da API na
  sessao.
- Cada janela pode faltar de forma independente, e o Claude Code remove uma
  janela assim que o `resets_at` dela passa.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

STATE_DIR = Path.home() / ".ccwidget"
STATE_PATH = STATE_DIR / "state.json"

# Cores ANSI (o Claude Code renderiza cores na status line).
DIM = "\033[2m"
RESET = "\033[0m"
ORANGE = "\033[38;5;173m"
GREEN = "\033[38;5;108m"
YELLOW = "\033[38;5;179m"
RED = "\033[38;5;167m"


def write_state(payload: dict) -> None:
    """Grava o estado de forma atomica, para o widget nunca ler um arquivo pela metade."""
    state = {
        "updated_at": time.time(),
        "session_id": payload.get("session_id"),
        "model": (payload.get("model") or {}).get("display_name"),
        "model_id": (payload.get("model") or {}).get("id"),
        "cwd": payload.get("cwd"),
        "version": payload.get("version"),
        "rate_limits": payload.get("rate_limits") or {},
        "cost": payload.get("cost") or {},
        "context_window": payload.get("context_window") or {},
        "prompt_cache": payload.get("prompt_cache") or {},
        "effort": (payload.get("effort") or {}).get("level"),
    }
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=STATE_DIR, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False)
        os.replace(tmp, STATE_PATH)
    except OSError:
        pass  # a status line nunca deve quebrar por causa do widget


def _color_for(pct: float) -> str:
    if pct >= 85:
        return RED
    if pct >= 60:
        return YELLOW
    return GREEN


def _bar(pct: float, width: int = 10) -> str:
    filled = int(round(min(max(pct, 0.0), 100.0) / 100 * width))
    return "█" * filled + "░" * (width - filled)


def _fmt_reset(epoch: float | None) -> str:
    if not epoch:
        return ""
    remaining = int(epoch - time.time())
    if remaining <= 0:
        return ""
    hours, minutes = divmod(remaining // 60, 60)
    return f"{hours}h{minutes:02d}" if hours else f"{minutes}min"


def render(payload: dict) -> str:
    parts: list[str] = []

    model = (payload.get("model") or {}).get("display_name")
    if model:
        parts.append(f"{ORANGE}◆ {model}{RESET}")

    ctx = payload.get("context_window") or {}
    used = ctx.get("used_percentage")
    if used is not None:
        parts.append(f"{_color_for(used)}ctx {used:.0f}%{RESET}")

    limits = payload.get("rate_limits") or {}
    five = limits.get("five_hour") or {}
    if five.get("used_percentage") is not None:
        pct = five["used_percentage"]
        reset = _fmt_reset(five.get("resets_at"))
        tail = f" {DIM}↻{reset}{RESET}" if reset else ""
        parts.append(f"{_color_for(pct)}5h {_bar(pct)} {pct:.0f}%{RESET}{tail}")

    week = limits.get("seven_day") or {}
    if week.get("used_percentage") is not None:
        pct = week["used_percentage"]
        parts.append(f"{_color_for(pct)}7d {pct:.0f}%{RESET}")

    cost = (payload.get("cost") or {}).get("total_cost_usd")
    if cost:
        parts.append(f"{DIM}${cost:.2f}{RESET}")

    return f" {DIM}│{RESET} ".join(parts)


def main() -> None:
    # O console do Windows usa cp1252 por padrao e nao consegue imprimir os
    # blocos da barra. Forcamos UTF-8 nos dois lados.
    for stream in (sys.stdin, sys.stdout):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
        return
    if not isinstance(payload, dict):
        return
    write_state(payload)
    line = render(payload)
    if line:
        try:
            print(line)
        except UnicodeEncodeError:  # console sem suporte a UTF-8
            print(line.encode("ascii", "replace").decode("ascii"))


if __name__ == "__main__":
    main()
