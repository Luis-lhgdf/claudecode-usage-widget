"""Tabela de precos dos modelos Claude e calculo de custo equivalente.

Os valores sao os precos publicos da API da Anthropic, em USD por milhao de
tokens (MTok). Regras de cache aplicadas sobre o preco de input:

    write 5m  = 1.25x input
    write 1h  = 2.00x input
    read      = 0.10x input  (excecao: Claude Fable 5.1 = 0.025x)

IMPORTANTE: quem usa Claude Code por assinatura (Pro/Max/Team) nao paga por
token. O custo calculado aqui e o *equivalente em API* -- serve para comparar
sessoes entre si e para estimar o peso de cada modelo no limite de uso, nao
para prever uma fatura.
"""

from dataclasses import dataclass

WRITE_5M_MULTIPLIER = 1.25
WRITE_1H_MULTIPLIER = 2.00
DEFAULT_READ_MULTIPLIER = 0.10


@dataclass(frozen=True)
class ModelPrice:
    """Preco de um modelo em USD por milhao de tokens."""

    input: float
    output: float
    cache_read: float | None = None  # None -> deriva de input * 0.10

    @property
    def read(self) -> float:
        if self.cache_read is not None:
            return self.cache_read
        return self.input * DEFAULT_READ_MULTIPLIER

    @property
    def write_5m(self) -> float:
        return self.input * WRITE_5M_MULTIPLIER

    @property
    def write_1h(self) -> float:
        return self.input * WRITE_1H_MULTIPLIER


# Precos por MTok. Chaves normalizadas (sem sufixo de data, minusculas).
PRICES: dict[str, ModelPrice] = {
    # Fable / Mythos
    "claude-fable-5-1": ModelPrice(10.00, 50.00, cache_read=0.25),
    "claude-mythos-5-1": ModelPrice(10.00, 50.00, cache_read=0.25),
    "claude-fable-5": ModelPrice(10.00, 50.00, cache_read=1.00),
    "claude-mythos-5": ModelPrice(10.00, 50.00, cache_read=1.00),
    # Opus
    "claude-opus-5": ModelPrice(5.00, 25.00),
    "claude-opus-4-8": ModelPrice(5.00, 25.00),
    "claude-opus-4-7": ModelPrice(5.00, 25.00),
    "claude-opus-4-6": ModelPrice(5.00, 25.00),
    "claude-opus-4-5": ModelPrice(5.00, 25.00),
    "claude-opus-4-1": ModelPrice(15.00, 75.00),
    "claude-opus-4": ModelPrice(15.00, 75.00),
    "claude-3-opus": ModelPrice(15.00, 75.00),
    # Sonnet
    "claude-sonnet-5": ModelPrice(2.00, 10.00),
    "claude-sonnet-4-6": ModelPrice(3.00, 15.00),
    "claude-sonnet-4-5": ModelPrice(3.00, 15.00),
    "claude-sonnet-4": ModelPrice(3.00, 15.00),
    "claude-3-7-sonnet": ModelPrice(3.00, 15.00),
    "claude-3-5-sonnet": ModelPrice(3.00, 15.00),
    # Haiku
    "claude-haiku-4-5": ModelPrice(1.00, 5.00),
    "claude-3-5-haiku": ModelPrice(0.80, 4.00),
    "claude-3-haiku": ModelPrice(0.25, 1.25),
}

# Usado quando o modelo do log nao bate com nenhuma entrada conhecida.
# Assume a faixa Opus, que e a mais comum no Claude Code.
FALLBACK_PRICE = ModelPrice(5.00, 25.00)


def normalize_model(model: str | None) -> str:
    """Reduz o id do modelo a chave da tabela.

    Remove sufixos de data (`-20250514`), prefixos de provedor
    (`anthropic.`, `us.anthropic.`) e sufixos de contexto (`[1m]`).
    """
    if not model:
        return ""
    name = model.strip().lower()
    for prefix in ("us.anthropic.", "eu.anthropic.", "apac.anthropic.", "anthropic."):
        if name.startswith(prefix):
            name = name[len(prefix) :]
    if "[" in name:  # claude-opus-5[1m]
        name = name.split("[", 1)[0]
    name = name.replace("@", "-")  # ids do Vertex: claude-opus-4-5@20251101
    parts = name.split("-")
    # descarta um sufixo final puramente numerico com cara de data (8 digitos)
    if parts and parts[-1].isdigit() and len(parts[-1]) >= 6:
        parts = parts[:-1]
    return "-".join(parts)


def price_for(model: str | None) -> ModelPrice:
    """Retorna o preco do modelo, com fallback por prefixo mais longo."""
    key = normalize_model(model)
    if key in PRICES:
        return PRICES[key]
    # tenta o match de prefixo mais especifico (ex.: claude-3-5-sonnet-latest)
    candidates = [k for k in PRICES if key.startswith(k)]
    if candidates:
        return PRICES[max(candidates, key=len)]
    return FALLBACK_PRICE


def cost_usd(
    model: str | None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_write_5m_tokens: int = 0,
    cache_write_1h_tokens: int = 0,
) -> float:
    """Custo equivalente em USD de uma requisicao."""
    p = price_for(model)
    return (
        input_tokens * p.input
        + output_tokens * p.output
        + cache_read_tokens * p.read
        + cache_write_5m_tokens * p.write_5m
        + cache_write_1h_tokens * p.write_1h
    ) / 1_000_000
