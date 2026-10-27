"""Jalankan peran Alice: python -m src.alice.main"""

import sys

sys.argv = [sys.argv[0], "--role", "alice", *sys.argv[1:]]
from src.main import main  # noqa: E402

if __name__ == "__main__":
    main()
