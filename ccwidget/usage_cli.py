"""A fonte de dados do widget: `claude -p "/usage"`.

O comando e local -- nao ha resposta de modelo, entao nao consome tokens --,
mas leva alguns segundos para o CLI iniciar. Por isso e chamado em intervalo
(dez minutos por padrao) e sob demanda, nunca no laco da interface.

Texto esperado:

    Current session: 27% used · resets Sep 2, 5:39pm (America/Sao_Paulo)
    Current week (all models): 4% used · resets Sep 8, 9:59pm (America/Sao_Paulo)
    Current week (Fable): 0% used
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9
    ZoneInfo = None  # type: ignore[assignment]

# "27% used · resets Sep 2, 5:39pm (America/Sao_Paulo)"
_PERCENT = r"(\d+(?:[.,]\d+)?)\s*%\s*used"
# `when` precisa ser guloso: com `+?` o motor casaria uma unica letra, ja que
# tudo depois dele e opcional, e a data nunca seria lida.
_RESET = r"(?:[^\S\n]*[·.•-][^\S\n]*resets\s+(?P<when>[^(\n]+)(?:\((?P<tz>[^)]+)\))?)?"

PATTERNS = {
    "five_hour": re.compile(r"Current session:\s*" + _PERCENT + _RESET, re.I),
    "seven_day": re.compile(
        r"Current week\s*\(all models\):\s*" + _PERCENT + _RESET, re.I
    ),
    "fable_week": re.compile(
        r"Current week\s*\(fable\):\s*" + _PERCENT + _RESET, re.I
    ),
}


def _parse_reset(when: str | None, tz_name: str | None) -> float | None:
    """Converte 'Sep 2, 5:39pm' + 'America/Sao_Paulo' em epoch segundos."""
    if not when:
        return None
    text = when.strip().rstrip(".").replace(",", " ")
    text = re.sub(r"\s+", " ", text)

    tz = None
    if tz_name and ZoneInfo is not None:
        try:
            tz = ZoneInfo(tz_name.strip())
        except Exception:
            tz = None
    if tz is None:
        tz = datetime.now().astimezone().tzinfo

    now = datetime.now(tz)
    for fmt in ("%b %d %I:%M%p", "%b %d %I%p", "%I:%M%p", "%H:%M"):
        try:
            # O texto vai em maiusculas porque strptime aceita "SEP"/"PM" nessa
            # forma; o formato NAO pode ser convertido junto (%d viraria %D,
            # uma diretiva invalida).
            parsed = datetime.strptime(text.upper(), fmt)
        except ValueError:
            continue
        if "%b" in fmt:
            dt = parsed.replace(year=now.year, tzinfo=tz)
            # Virada de ano: "Jan 3" visto em dezembro pertence ao ano seguinte.
            if dt < now - timedelta(days=180):
                dt = dt.replace(year=now.year + 1)
        else:
            dt = now.replace(
                hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0
            )
            if dt < now:
                dt += timedelta(days=1)
        return dt.timestamp()
    return None


def parse_usage_output(text: str) -> dict:
    """Extrai as janelas de limite do texto do `/usage`."""
    limits: dict[str, dict] = {}
    for key, pattern in PATTERNS.items():
        match = pattern.search(text)
        if not match:
            continue
        window: dict = {"used_percentage": float(match.group(1).replace(",", "."))}
        resets_at = _parse_reset(
            match.groupdict().get("when"), match.groupdict().get("tz")
        )
        if resets_at:
            window["resets_at"] = resets_at
        limits[key] = window
    return limits


def fetch(timeout: int = 90, executable: str = "claude") -> dict:
    """Roda o comando e devolve as janelas encontradas.

    Levanta RuntimeError com uma mensagem curta quando falha, para o widget
    poder mostrar o motivo sem quebrar.
    """
    try:
        proc = subprocess.run(
            [executable, "-p", "/usage"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            # No Windows, evita piscar uma janela de console.
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError:
        raise RuntimeError("comando 'claude' não encontrado no PATH") from None
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"'claude -p /usage' passou de {timeout}s") from None

    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    limits = parse_usage_output(output)
    if not limits:
        snippet = " ".join(output.split())[:120]
        raise RuntimeError(f"não encontrei percentuais na saída: {snippet or 'vazia'}")
    return limits


def refresh_state(state_path=None) -> dict:
    """Consulta o `/usage` e grava o resultado onde o widget le.

    A escrita e atomica, para o widget nunca ler um arquivo pela metade. O
    conteudo anterior e substituido por inteiro: o que a consulta nao devolveu
    nao vale mais.
    """
    from .state import STATE_PATH

    target = Path(state_path) if state_path else STATE_PATH
    limits = fetch()
    estado = {"updated_at": time.time(), "rate_limits": limits}

    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(estado, fh, ensure_ascii=False)
    os.replace(tmp, target)
    return limits
