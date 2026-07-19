@echo off
REM Excel Formula AI Assistant — Windows 构建脚本
REM
REM 用法:
REM   .\desktop\build-win.bat
REM
REM 输出:
REM   dist\ExcelFormulaAI.exe   ← Windows 可执行文件

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
set "DIST_DIR=%PROJECT_DIR%\dist"

echo ================================================
echo   📦 构建 Excel 公式助手 - Windows
echo ================================================
echo.

REM ---- Step 1: 构建 React 前端 ----
echo 📊 Step 1/4: 构建 React 前端...
cd /d "%PROJECT_DIR%\addin"
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo ❌ React 构建失败
    exit /b 1
)
echo    ✅ addin\dist\ 已生成
echo.

REM ---- Step 2: 复制静态文件 ----
echo 📁 Step 2/4: 部署静态文件...
if exist "%SCRIPT_DIR%static" rmdir /s /q "%SCRIPT_DIR%static"
xcopy /e /i "%PROJECT_DIR%\addin\dist" "%SCRIPT_DIR%static"
copy "%PROJECT_DIR%\addin\public\icon.png" "%SCRIPT_DIR%icon.png" >nul 2>&1
echo    ✅ 静态文件已部署到 desktop\static\
echo.

REM ---- Step 3: PyInstaller 打包 ----
echo 🔧 Step 3/4: PyInstaller 打包...
cd /d "%PROJECT_DIR%"
python -m PyInstaller "%SCRIPT_DIR%ExcelFormulaAI.spec" --clean --noconfirm --distpath "%DIST_DIR%" --workpath "%PROJECT_DIR%\build\pyinstaller"
if %ERRORLEVEL% NEQ 0 (
    echo ❌ PyInstaller 打包失败
    exit /b 1
)
echo    ✅ .exe 已生成: %DIST_DIR%\ExcelFormulaAI.exe
echo.

REM ---- Step 4: 清理 ----
echo 🧹 Step 4/4: 清理构建缓存...
rmdir /s /q "%PROJECT_DIR%\build" 2>nul
echo    ✅ 完成

echo.
echo ================================================
echo   🎉 构建成功！
echo   应用: %DIST_DIR%\ExcelFormulaAI.exe
echo ================================================
