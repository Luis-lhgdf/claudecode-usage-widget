"""Leitura incremental dos logs de sessao do Claude Code.

O Claude Code grava um JSONL por sessao em ~/.claude/projects/<projeto>/<id>.jsonl.
Cada resposta do modelo aparece como uma ou mais linhas `type: "assistant"`.

Duas armadilhas que este modulo resolve:

1. **Linhas duplicadas.** Uma unica resposta da API costuma ser gravada em
   varias linhas (uma por bloco de conteudo), todas repetindo o mesmo objeto
   `usage`. Somar linha a linha infla o consumo em cerca de 3x. A deduplicacao
   usa o `requestId`, com fallback para `message.id`.

2. **Custo de releitura.** Reprocessar centenas de arquivos a cada atualizacao
   e lento. O coletor guarda o offset em bytes ja lido de cada arquivo e so le
   o que foi acrescentado desde a ultima passada.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


def default_projects_dir() -> Path:
    """Diretorio de sessoes, respeitando CLAUDE_CONFIG_DIR."""
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    base = Path(env) if env else Path.home() / ".claude"
    return base / "projects"


@dataclass(slots=True)
class Request:
    """Uma requisicao ja deduplicada, com tokens e custo equivalente."""

    ts: datetime  # sempre em UTC
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_5m_tokens: int
    cache_write_1h_tokens: int
    cost: float
    project: str
    session_id: str

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_5m_tokens
            + self.cache_write_1h_tokens
        )


@dataclass(slots=True)
class _FileState:
    offset: int = 0
    size: int = 0


class Collector:
    """Mantem em memoria as requisicoes recentes, atualizando de forma incremental."""

    def __init__(self, projects_dir: Path | None = None, history_days: int = 30) -> None:
        self.projects_dir = projects_dir or default_projects_dir()
        self.history_days = history_days
        self.requests: list[Request] = []
        self._files: dict[str, _FileState] = {}
        self._seen: set[str] = set()

    # ------------------------------------------------------------------ API

    def refresh(self) -> int:
        """Le o que ha de novo. Retorna quantas requisicoes foram adicionadas."""
        from .pricing import cost_usd  # import tardio: evita ciclo de importacao

        if not self.projects_dir.is_dir():
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.history_days)
        cutoff_epoch = cutoff.timestamp()
        added = 0

        for path in self.projects_dir.glob("*/*.jsonl"):
            try:
                stat = path.stat()
            except OSError:
                continue

            key = str(path)
            state = self._files.get(key)

            # Arquivo nunca visto e antigo demais: registra como lido sem abrir.
            if state is None and stat.st_mtime < cutoff_epoch:
                self._files[key] = _FileState(offset=stat.st_size, size=stat.st_size)
                continue

            if state is None:
                state = _FileState()
                self._files[key] = state
            elif stat.st_size == state.size:
                continue  # nada novo neste arquivo
            elif stat.st_size < state.size:
                state.offset = 0  # arquivo truncado ou rotacionado: le de novo

            for record in self._read_new_lines(path, state):
                req = self._parse(record, cost_usd)
                if req is not None and req.ts >= cutoff:
                    self.requests.append(req)
                    added += 1

            state.size = stat.st_size

        if added:
            self.requests.sort(key=lambda r: r.ts)
        return added

    def prune(self) -> None:
        """Descarta requisicoes que sairam da janela de historico."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.history_days)
        if self.requests and self.requests[0].ts < cutoff:
            self.requests = [r for r in self.requests if r.ts >= cutoff]

    # -------------------------------------------------------------- interno

    def _read_new_lines(self, path: Path, state: _FileState):
        """Gera os objetos JSON ainda nao lidos, avancando o offset com seguranca."""
        try:
            with path.open("rb") as fh:
                fh.seek(state.offset)
                chunk = fh.read()
        except OSError:
            return

        if not chunk:
            return

        # A ultima linha pode estar incompleta (sessao escrevendo agora), entao
        # so consumimos ate o ultimo \n e deixamos o resto para a proxima passada.
        last_newline = chunk.rfind(b"\n")
        if last_newline == -1:
            return
        consumed = chunk[: last_newline + 1]
        state.offset += len(consumed)

        needle = b'"type":"assistant"'
        needle_spaced = b'"type": "assistant"'
        for raw in consumed.split(b"\n"):
            if not raw.strip():
                continue
            # Filtro barato antes do json.loads: a maioria das linhas nao serve.
            if needle not in raw and needle_spaced not in raw:
                continue
            try:
                yield json.loads(raw.decode("utf-8", "replace"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

    def _parse(self, record: dict, cost_usd) -> Request | None:
        if record.get("type") != "assistant":
            return None

        message = record.get("message") or {}
        usage = message.get("usage") or {}
        if not usage:
            return None

        req_id = record.get("requestId") or message.get("id")
        if not req_id or req_id in self._seen:
            return None

        ts_raw = record.get("timestamp")
        if not ts_raw:
            return None
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except ValueError:
            return None
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ts = ts.astimezone(timezone.utc)

        model = message.get("model") or ""
        if model == "<synthetic>":  # resposta local do proprio CLI, sem custo
            return None

        self._seen.add(req_id)

        creation = usage.get("cache_creation") or {}
        write_5m = int(creation.get("ephemeral_5m_input_tokens") or 0)
        write_1h = int(creation.get("ephemeral_1h_input_tokens") or 0)
        total_write = int(usage.get("cache_creation_input_tokens") or 0)
        if not creation and total_write:
            write_5m = total_write  # logs antigos nao separam por TTL

        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        cache_read = int(usage.get("cache_read_input_tokens") or 0)

        cwd = record.get("cwd") or ""
        project = Path(cwd).name if cwd else "-"

        return Request(
            ts=ts,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read,
            cache_write_5m_tokens=write_5m,
            cache_write_1h_tokens=write_1h,
            cost=cost_usd(
                model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read,
                cache_write_5m_tokens=write_5m,
                cache_write_1h_tokens=write_1h,
            ),
            project=project,
            session_id=record.get("sessionId") or "",
        )
