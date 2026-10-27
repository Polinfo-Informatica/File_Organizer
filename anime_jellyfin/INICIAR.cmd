@echo off
setlocal
cd /d "%~dp0"
python -c "import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 (
    python -X utf8 "%~dp0run_local.py" %*
    goto :done
)
py -3 -c "import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 (
    py -3 -X utf8 "%~dp0run_local.py" %*
    goto :done
)
echo Python 3.10 or newer was not found. Install Python and enable the PATH option.
:done
if /i "%~1"=="--check" exit /b
pause
