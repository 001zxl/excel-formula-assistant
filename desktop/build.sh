#!/bin/bash
# Excel Formula AI Assistant — macOS App 构建脚本
#
# 用法:
#   chmod +x desktop/build.sh
#   ./desktop/build.sh
#
# 输出:
#   dist/ExcelFormulaAI.app   ← 应用程序
#   dist/ExcelFormulaAI.dmg   ← 分发包

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
DIST_DIR="$PROJECT_DIR/dist"

echo "================================================"
echo "  📦 构建 Excel 公式助手 - macOS App"
echo "================================================"
echo ""

# ---- 检查 ----
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ 虚拟环境未找到: $VENV_PYTHON"
    echo "   请先运行: cd $PROJECT_DIR && uv venv --python 3.10 && uv pip install -r desktop/requirements.txt"
    exit 1
fi

# ---- Step 1: 构建 React 前端 ----
echo "📊 Step 1/5: 构建 React 前端..."
cd "$PROJECT_DIR/addin"
npm run build 2>&1 | tail -3
echo "   ✅ addin/dist/ 已生成"
echo ""

# ---- Step 2: 复制静态文件 ----
echo "📁 Step 2/5: 部署静态文件..."
rm -rf "$SCRIPT_DIR/static"
cp -r "$PROJECT_DIR/addin/dist" "$SCRIPT_DIR/static"
cp "$PROJECT_DIR/addin/public/icon.png" "$SCRIPT_DIR/icon.png" 2>/dev/null || true
echo "   ✅ 静态文件已部署到 desktop/static/"
echo ""

# ---- Step 3: PyInstaller 打包 ----
echo "🔧 Step 3/5: PyInstaller 打包（此步骤需要数分钟）..."
cd "$PROJECT_DIR"
"$VENV_PYTHON" -m PyInstaller \
    "$SCRIPT_DIR/ExcelFormulaAI.spec" \
    --clean \
    --noconfirm \
    --distpath "$DIST_DIR" \
    --workpath "$PROJECT_DIR/build/pyinstaller" \
    2>&1 | tail -5
echo "   ✅ .app 已生成: $DIST_DIR/ExcelFormulaAI.app"
echo ""

# ---- Step 4: 创建 DMG ----
echo "💿 Step 4/5: 创建 DMG 安装包..."
DMG_PATH="$DIST_DIR/ExcelFormulaAI.dmg"
rm -f "$DMG_PATH"

# 在临时目录中创建 DMG 布局
TMP_DMG="$(mktemp -d)"
cp -R "$DIST_DIR/ExcelFormulaAI.app" "$TMP_DMG/"
# 创建 Applications 快捷方式
ln -s /Applications "$TMP_DMG/Applications"

hdiutil create \
    -volname "Excel公式助手" \
    -srcfolder "$TMP_DMG" \
    -ov \
    -format UDZO \
    "$DMG_PATH" 2>&1 | tail -3

rm -rf "$TMP_DMG"
echo "   ✅ DMG 已生成: $DMG_PATH"
echo ""

# ---- Step 5: 清理 ----
echo "🧹 Step 5/5: 清理构建缓存..."
rm -rf "$PROJECT_DIR/build"
echo "   ✅ 完成"

# ---- 结果 ----
echo ""
echo "================================================"
echo "  🎉 构建成功！"
echo ""
echo "  应用:  $DIST_DIR/ExcelFormulaAI.app"
echo "  安装包: $DMG_PATH"
echo ""
echo "  大小:"
ls -lh "$DIST_DIR/ExcelFormulaAI.app" 2>/dev/null
ls -lh "$DMG_PATH" 2>/dev/null
echo ""
echo "  在 Finder 中打开:"
echo "    open '$DIST_DIR'"
echo "================================================"
