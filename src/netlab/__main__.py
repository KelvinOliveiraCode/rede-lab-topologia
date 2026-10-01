"""Permite executar como ``python -m netlab``.

Enables running as ``python -m netlab``.
"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())