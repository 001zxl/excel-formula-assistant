#!/usr/bin/env python3
"""Excel Formula MCP Server 启动脚本。

用法:
  python run_server.py
  或注册到 Claude Code 的 .mcp.json 中。
"""

import sys
from pathlib import Path

# 确保项目根在 path 中
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp_server.server import main

if __name__ == "__main__":
    main()
