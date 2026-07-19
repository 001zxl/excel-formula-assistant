#!/bin/bash
# Excel Formula AI Assistant — 一键启动
# 启动后:
#   1. 本地代理: https://localhost:8100 (AI API 代理)
#   2. 插件开发服务器: https://localhost:3000 (Excel 侧边栏)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "  Excel Formula AI Assistant"
echo "================================================"

PYTHON="$SCRIPT_DIR/.venv/bin/python"

# 检查虚拟环境
if [ ! -f "$PYTHON" ]; then
    echo "❌ 虚拟环境未找到！请先运行: cd $SCRIPT_DIR && uv venv --python 3.10 && uv pip install mcp httpx openpyxl fastapi uvicorn"
    exit 1
fi

# 启动本地代理（后台）
echo ""
echo "🔐 启动本地 AI 代理: https://localhost:8100"
$PYTHON local_proxy/server.py &
PROXY_PID=$!
sleep 1

# 启动插件开发服务器
echo ""
echo "📊 启动 Excel 插件开发服务器: https://localhost:3000"
cd addin
npx vite --port 3000 --https &
VITE_PID=$!

echo ""
echo "================================================"
echo "  ✅ 服务已启动"
echo ""
echo "  本地代理:   https://localhost:8100"
echo "  插件页面:   https://localhost:3000"
echo ""
echo "  在 Excel 中加载插件:"
echo "    1. 打开 Excel"
echo "    2. 插入 → 加载项 → 我的加载项"
echo "    3. 上传 manifest.xml 文件:"
echo "       $SCRIPT_DIR/addin/manifest.xml"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "================================================"

# 等待中断
trap "kill $PROXY_PID $VITE_PID 2>/dev/null; echo '已停止所有服务'" EXIT
wait
