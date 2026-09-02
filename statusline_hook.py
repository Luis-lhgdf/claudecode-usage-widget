"""Entrada da status line, para ser chamada pelo Claude Code.

Configure em ~/.claude/settings.json:

    "statusLine": {
      "type": "command",
      "command": "python \"C:\\\\caminho\\\\para\\\\statusline_hook.py\""
    }

O script `scripts/install-statusline.ps1` faz isso para voce.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ccwidget.statusline import main  # noqa: E402

if __name__ == "__main__":
    main()
