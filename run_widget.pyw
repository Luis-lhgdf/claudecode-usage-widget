"""Abre o widget sem janela de console.

A extensao .pyw faz o Windows usar o pythonw.exe, que nao abre terminal.
Use este arquivo no atalho da area de trabalho e na inicializacao automatica.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ccwidget.ui import run  # noqa: E402

if __name__ == "__main__":
    run()
