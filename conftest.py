"""Đảm bảo pytest luôn import được package `src`.

Trên máy cá nhân thường vẫn chạy được nhờ thư mục hiện hành nằm sẵn trong
`sys.path`, nhưng trên CI thì không — nên test xanh ở local mà đỏ trên CI.
File này đặt ở gốc repo nên pytest luôn nạp trước khi thu thập test.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
