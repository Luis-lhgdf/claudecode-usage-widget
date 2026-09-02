"""Agregacao das requisicoes em janelas de uso.

O Claude Code aplica dois limites: uma **sessao de 5 horas**, que comeca na
primeira mensagem e expira 5 horas depois, e um **limite semanal**, que reinicia
num dia e hora fixos da conta.

Sobre precisao: as janelas aqui sao reconstruidas a partir dos logs desta
maquina. Se voce usou o Claude Code em outro dispositivo ou no claude.ai, o
inicio real do bloco pode ser anterior ao que os logs locais mostram -- o
proprio `/usage` faz a mesma ressalva. Por isso a configuracao permite ancorar
o bloco manualmente com o horario de reset exibido pelo `/usage`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .collector import Request

BLOCK_HOURS = 5


@dataclass(slots=True)
class Totals:
    """Soma de tokens e custo de um conjunto de requisicoes."""

    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost: float = 0.0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )

    def add(self, req: Request) -> None:
        self.requests += 1
        self.input_tokens += req.input_tokens
        self.output_tokens += req.output_tokens
        self.cache_read_tokens += req.cache_read_tokens
        self.cache_write_tokens += req.cache_write_5m_tokens + req.cache_write_1h_tokens
        self.cost += req.cost


@dataclass(slots=True)
class Block:
    """Uma janela de 5 horas."""

    start: datetime
    last_activity: datetime
    totals: Totals = field(default_factory=Totals)

    @property
    def end(self) -> datetime:
        return self.start + timedelta(hours=BLOCK_HOURS)

    def is_active(self, now: datetime | None = None) -> bool:
        return (now or datetime.now(timezone.utc)) < self.end

    def remaining(self, now: datetime | None = None) -> timedelta:
        delta = self.end - (now or datetime.now(timezone.utc))
        return max(delta, timedelta(0))

    def elapsed_fraction(self, now: datetime | None = None) -> float:
        """Fracao do tempo da janela ja decorrida, de 0.0 a 1.0."""
        now = now or datetime.now(timezone.utc)
        total = BLOCK_HOURS * 3600
        return min(max((now - self.start).total_seconds() / total, 0.0), 1.0)


def build_blocks(requests: list[Request]) -> list[Block]:
    """Agrupa requisicoes em janelas de 5 horas.

    Uma nova janela comeca quando a requisicao cai fora da janela anterior.
    As requisicoes devem estar ordenadas por horario.
    """
    blocks: list[Block] = []
    for req in requests:
        if not blocks or req.ts >= blocks[-1].end:
            blocks.append(Block(start=req.ts, last_activity=req.ts))
        block = blocks[-1]
        block.last_activity = req.ts
        block.totals.add(req)
    return blocks


def current_block(
    requests: list[Request],
    now: datetime | None = None,
    anchor: datetime | None = None,
) -> Block | None:
    """Devolve a janela de 5 horas em curso, ou None se nao houver uma ativa.

    Se `anchor` for informado (o inicio real do bloco, derivado do horario de
    reset que o `/usage` mostra), a janela usa esse inicio em vez de inferir
    pelos logs.
    """
    now = now or datetime.now(timezone.utc)

    if anchor is not None and anchor <= now < anchor + timedelta(hours=BLOCK_HOURS):
        block = Block(start=anchor, last_activity=anchor)
        for req in requests:
            if anchor <= req.ts < block.end:
                block.last_activity = req.ts
                block.totals.add(req)
        return block

    blocks = build_blocks(requests)
    if blocks and blocks[-1].is_active(now):
        return blocks[-1]
    return None


def week_period(
    anchor: datetime | None, now: datetime | None = None
) -> tuple[datetime, datetime]:
    """Periodo semanal em curso.

    `anchor` e qualquer instante de reset conhecido (o `/usage` informa um, por
    exemplo "Reinicia ter., 22:00"); o periodo atual e a janela de 7 dias
    alinhada a ele. Sem ancora, cai para os ultimos 7 dias corridos.
    """
    now = now or datetime.now(timezone.utc)
    if anchor is None:
        return now - timedelta(days=7), now

    week = timedelta(days=7)
    delta = now - anchor
    periods = delta // week  # divisao inteira, funciona para ancora futura tambem
    start = anchor + periods * week
    if start > now:
        start -= week
    return start, start + week


def totals_between(
    requests: list[Request], start: datetime, end: datetime
) -> Totals:
    totals = Totals()
    for req in requests:
        if start <= req.ts < end:
            totals.add(req)
    return totals


def group_by(
    requests: list[Request], key: str, start: datetime, end: datetime, limit: int = 5
) -> list[tuple[str, Totals]]:
    """Agrupa por atributo (`project` ou `model`) no intervalo, do maior custo ao menor."""
    groups: dict[str, Totals] = defaultdict(Totals)
    for req in requests:
        if start <= req.ts < end:
            groups[getattr(req, key) or "-"].add(req)
    ordered = sorted(groups.items(), key=lambda kv: kv[1].cost, reverse=True)
    return ordered[:limit]


def daily_costs(requests: list[Request], days: int, tz) -> list[tuple[str, float]]:
    """Custo por dia nos ultimos `days` dias, no fuso local, do mais antigo ao mais novo."""
    today = datetime.now(tz).date()
    buckets: dict[str, float] = {}
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        buckets[day.isoformat()] = 0.0
    for req in requests:
        key = req.ts.astimezone(tz).date().isoformat()
        if key in buckets:
            buckets[key] += req.cost
    return list(buckets.items())
