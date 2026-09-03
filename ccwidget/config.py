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
    # Intervalo entre consultas automaticas ao `claude -p /usage`, em minutos.
    # Aceita fracao: 0.5 sao os 30 segundos oferecidos no menu. 0 deixa a busca
    # so no menu -- mas a primeira consulta, ao abrir a janela, acontece de
    # qualquer forma. O comando nao consome tokens; inicia o CLI a cada vez,
    # entao os intervalos curtos cobram alguns segundos de CPU por consulta.
    usage_refresh_minutes: float = 10

    # Versao registrada pelo instalador, para ele saber o que ja esta na
    # maquina e decidir entre instalar, atualizar ou reinstalar.
    installed_version: str | None = None

    # --- aviso de versao nova ----------------------------------------------
    # Uma vez por dia o widget le a versao publicada no GitHub e avisa quando
    # ha uma mais nova que a instalada. Desligado, nenhuma requisicao sai da
    # maquina. Veja ccwidget/update_check.py.
    update_check: bool = True
    # Quando foi a ultima consulta e o que ela devolveu. O resultado fica
    # guardado para o aviso aparecer nas aberturas seguintes sem rede.
    update_checked_at: float = 0.0
    update_latest: str | None = None

    # --- janela ------------------------------------------------------------
    # mode: "mini" (so o circulo) ou "panel" (sessao e semana).
    mode: str = "panel"
    # theme: "dark", "light" ou "auto" (segue a preferencia do Windows).
    theme: str = "auto"
    # Com as animacoes desligadas o widget abre e fecha na hora, e o mascote
    # para de fazer gracinhas no modo minimizado.
    animations: bool = True
    # Aparencia do mascote: veja theme.SKINS.
    skin: str = "classico"
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

