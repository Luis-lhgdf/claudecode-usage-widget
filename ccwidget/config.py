"""Configuracao persistente do widget.

Guardada em ~/.ccwidget/config.json. Todos os campos tem padrao razoavel: o
widget funciona sem nenhuma configuracao previa.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
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
    # Intervalo entre consultas automaticas ao `claude -p /usage`, em minutos.
    # 0 desliga e deixa a busca so no menu. O comando nao consome tokens, mas
    # inicia o CLI a cada vez, entao nao vale rodar de minuto em minuto.
    usage_refresh_minutes: int = 10

    # --- janela ------------------------------------------------------------
    # mode: "mini" (so o circulo), "summary" (sessao + semana) ou "full".
    mode: str = "summary"
    # theme: "dark", "light" ou "auto" (segue a preferencia do Windows).
    theme: str = "auto"
    # Altura em que a gaveta fica encostada na borda direita.
    drawer_y: int = 220
    pos_x: int = 40
    pos_y: int = 40
    opacity: float = 0.96
    always_on_top: bool = True

    # ---------------------------------------------------------------- infra

    @classmethod
    def load(cls) -> "Config":
        try:
            # utf-8-sig: o PowerShell grava UTF-8 com BOM, e um BOM faria o
            # json.loads falhar, descartando a configuracao em silencio.
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, ValueError):
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

