"""Aviso de versao nova.

O widget roda do proprio diretorio do repositorio: atualizar e um `git pull`
seguido do instalador, e nada na tela lembrava disso -- quem clonou em marco
seguia com a versao de marco sem saber que havia outra.

Uma vez por dia, o widget le a versao publicada no GitHub e compara com a
daqui. A consulta e um GET de um arquivo de texto publico: nada e enviado
alem do pedido, e qualquer falha -- sem rede, proxy no caminho, GitHub fora,
resposta estranha -- devolve None em silencio. Um aviso de atualizacao nao
tem o direito de estragar a tela nem de segurar a interface.

O usuario pode desligar a checagem no menu; desligada, nenhuma requisicao
sai da maquina.
"""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

from . import __version__

# Onde a versao publicada e lida. Num fork, troque o caminho do repositorio.
REPO = "Luis-lhgdf/claudecode-usage-widget"
VERSION_URL = (
    f"https://raw.githubusercontent.com/{REPO}/main/ccwidget/__init__.py"
)

# Uma vez por dia basta: o projeto nao publica de hora em hora, e a resposta
# fica guardada na configuracao entre as consultas.
CHECK_EVERY_SECONDS = 24 * 3600
TIMEOUT_SECONDS = 8

# Raiz do repositorio -- ccwidget/update_check.py -> ccwidget/ -> raiz.
REPO_DIR = Path(__file__).resolve().parents[1]

_VERSION_RE = re.compile(r"""__version__\s*=\s*["']([^"']+)["']""")


def _partes(versao: str | None) -> tuple[int, ...] | None:
    """"0.4.1" -> (0, 4, 1). Devolve None quando nao ha numero algum."""
    numeros = re.findall(r"\d+", versao or "")
    if not numeros:
        return None
    return tuple(int(n) for n in numeros)


def is_newer(remota: str | None, local: str = __version__) -> bool:
    """A versao remota e maior que a local?

    Compara com o mesmo numero de componentes, para "0.5" e "0.5.0" empatarem
    em vez de a mais curta parecer menor.
    """
    a, b = _partes(remota), _partes(local)
    if a is None or b is None:
        return False
    tamanho = max(len(a), len(b))
    a += (0,) * (tamanho - len(a))
    b += (0,) * (tamanho - len(b))
    return a > b


def nova_versao(guardada: str | None, local: str = __version__) -> str | None:
    """A versao guardada, se ainda for novidade. Serve para ler o cache.

    Depois de atualizar, a versao local alcanca a guardada e o aviso
    desaparece sozinho -- sem depender de uma nova consulta.
    """
    return guardada if is_newer(guardada, local) else None


def fetch_latest(url: str = VERSION_URL, timeout: int = TIMEOUT_SECONDS) -> str | None:
    """Le a versao publicada. Nunca levanta excecao: falha vira None.

    Roda numa thread, longe do laco da interface -- uma rede lenta prenderia
    a janela pelo tempo do timeout.
    """
    pedido = urllib.request.Request(
        url, headers={"User-Agent": f"cc-widget/{__version__}"}
    )
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
            # Limite de leitura: o arquivo tem algumas centenas de bytes, e
            # nao ha razao para engolir o que vier de um endereco trocado.
            texto = resposta.read(4096).decode("utf-8", "replace")
    except Exception:
        return None

    encontrado = _VERSION_RE.search(texto)
    return encontrado.group(1).strip() if encontrado else None


def comando_de_atualizacao(repo: Path = REPO_DIR) -> str:
    """Linha de PowerShell que puxa o codigo novo e reinstala."""
    return f'cd "{repo}"; git pull; .\scripts\install.ps1'
