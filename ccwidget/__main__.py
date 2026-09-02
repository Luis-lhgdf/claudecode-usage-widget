"""Ponto de entrada.

    python -m ccwidget          abre o widget flutuante
    python -m ccwidget usage    consulta o /usage e grava para o widget
    python -m ccwidget report   imprime os percentuais no terminal
"""

from __future__ import annotations

import sys

LABELS = {
    "five_hour": "Sessão",
    "seven_day": "Semana",
    "fable_week": "Semana (Fable)",
}


def _bar(pct: float, width: int = 28) -> str:
    filled = int(round(min(max(pct, 0), 100) / 100 * width))
    return "█" * filled + "░" * (width - filled)


def _report() -> None:
    """Os mesmos numeros do widget, sem abrir janela."""
    from datetime import datetime

    from .config import local_timezone
    from .state import read_state

    tz = local_timezone()
    live = read_state()

    print()
    print("  USO DO CLAUDE CODE")
    print("  " + "─" * 46)

    if not live.available:
        print("  Nenhuma consulta ainda — rode: python -m ccwidget usage")
        print()
        return

    for window, label in ((live.five_hour, "Sessão"), (live.seven_day, "Semana")):
        if window is None or window.expired:
            continue
        print(
            f"  {label:<9} {_bar(window.used_percentage)}"
            f" {window.used_percentage:5.1f}%"
        )
        if window.resets_at:
            clock = datetime.fromtimestamp(window.resets_at, tz=tz)
            print(f"            reinicia {clock:%d/%m %H:%M}")

    print("  " + "─" * 46)
    idade = int(live.age_seconds)
    quando = "agora" if idade < 60 else f"há {idade // 60} min"
    print(f"  /usage consultado {quando}{' (dado antigo)' if live.stale else ''}")
    print()


def _usage() -> None:
    from .usage_cli import refresh_state

    try:
        limits = refresh_state()
    except RuntimeError as exc:
        print(f"  falhou: {exc}")
        raise SystemExit(1)

    print()
    for key, window in limits.items():
        print(f"  {LABELS.get(key, key):<15} {window['used_percentage']:5.1f}%")
    print()
    print("  gravado em ~/.ccwidget/state.json")
    print()


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else ""

    if command == "report":
        _report()
    elif command == "usage":
        _usage()
    elif command in ("-h", "--help", "help"):
        print(__doc__)
    else:
        from .ui import run

        run()


if __name__ == "__main__":
    main()
