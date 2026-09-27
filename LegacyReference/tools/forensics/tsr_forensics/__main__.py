"""Permite ``python -m tsr_forensics <comando>``."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
