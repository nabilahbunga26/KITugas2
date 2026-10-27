"""Jalankan peran Bob: python -m src.bob.main"""

import sys

sys.argv = [sys.argv[0], "--role", "bob", *sys.argv[1:]]
from src.main import main  # noqa: E402

if __name__ == "__main__":
    main()
