"""Ponto de entrada.

    python -m ccwidget            abre o widget flutuante
    python -m ccwidget report     imprime o mesmo resumo no terminal
    python -m ccwidget statusline usado pelo Claude Code (le JSON do stdin)
"""

from __future__ import annotations

import sys


def _report() -> None:
    """Resumo em texto: util para conferir os numeros sem abrir a janela."""
    from datetime import datetime, timedelta, timezone

    from .analytics import current_block, group_by, totals_between, week_period
    from .collector import Collector
    from .config import Config, local_timezone
    from .state import read_state

    cfg = Config.load()
    tz = local_timezone()
    collector = Collector(history_days=cfg.history_days)
    collector.refresh()
    live = read_state()
    now = datetime.now(timezone.utc)

    def bar(pct: float, width: int = 28) -> str:
        filled = int(round(min(max(pct, 0), 100) / 100 * width))
        return "█" * filled + "░" * (width - filled)

    print()
    print("  CLAUDE CODE USAGE")
    print("  " + "─" * 46)

    # Sessao de 5 horas
    five = live.five_hour if live.five_hour and not live.five_hour.expired else None
    if five:
        reset = (
            datetime.fromtimestamp(five.resets_at, tz=tz).strftime("%H:%M")
            if five.resets_at
            else "--"
        )
        print(f"  Session   {bar(five.used_percentage)} {five.used_percentage:5.1f}%")
        print(f"            resets {reset}")
    else:
        print("  Session   (sem dado oficial — instale a status line)")

    # Semana
    week = live.seven_day if live.seven_day and not live.seven_day.expired else None
    if week:
        reset = (
            datetime.fromtimestamp(week.resets_at, tz=tz).strftime("%a %d/%m %H:%M")
            if week.resets_at
            else "--"
        )
        print(f"  Week      {bar(week.used_percentage)} {week.used_percentage:5.1f}%")
        print(f"            resets {reset}")

    # Bloco atual pelos logs locais
    block = current_block(collector.requests, now=now, anchor=cfg.block_anchor_dt())
    print("  " + "─" * 46)
    if block:
        print(
            f"  Bloco 5h  {block.totals.requests} reqs · "
            f"{block.totals.total_tokens:,} tokens · "
            f"~${block.totals.cost:,.2f} equivalente"
        )
        print(
            f"            inicio {block.start.astimezone(tz):%H:%M} · "
            f"reset ~{block.end.astimezone(tz):%H:%M}"
        )
    else:
        print("  Bloco 5h  nenhuma sessao ativa")

    # Semana pelos logs
    if week and week.resets_at:
        end = datetime.fromtimestamp(week.resets_at, tz=timezone.utc)
        start = end - timedelta(days=7)
    else:
        start, end = week_period(cfg.weekly_anchor_dt(), now)
    totals = totals_between(collector.requests, start, end)
    print(
        f"  Semana    {totals.requests} reqs · "
        f"{totals.total_tokens:,} tokens · ~${totals.cost:,.2f} equivalente"
    )

    top = group_by(collector.requests, "project", start, end, limit=5)
    if top:
        print("  " + "─" * 46)
        print("  Projetos (semana)")
        for name, t in top:
            print(f"    {name[:28]:<28} ~${t.cost:>8,.2f}")

    models = group_by(collector.requests, "model", start, end, limit=5)
    if models:
        print("  Modelos (semana)")
        for name, t in models:
            print(f"    {name[:28]:<28} ~${t.cost:>8,.2f}")

    print("  " + "─" * 46)
    if live.available:
        origem = "status line" + (" (dado antigo)" if live.stale else "")
    else:
        origem = "apenas logs locais"
    print(f"  Percentuais: {origem}")
    print(
        "  Valores com ~ sao estimativas de equivalente API, "
        "nao cobranca real.\n"
    )


def main() -> None:
    argv = sys.argv[1:]
    command = argv[0] if argv else ""

    if command == "statusline":
        from .statusline import main as statusline_main

        statusline_main()
    elif command == "report":
        _report()
    elif command in ("-h", "--help", "help"):
        print(__doc__)
    else:
        from .ui import run

        run()


if __name__ == "__main__":
    main()
