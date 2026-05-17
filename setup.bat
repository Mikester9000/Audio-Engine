@echo off
setlocal

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

echo [1/5] Checking Python installation...
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.11+ is required but was not found on PATH.
    echo Download Python from: https://www.python.org/downloads/windows/
    exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.11+ is required.
    python --version
    echo Download Python from: https://www.python.org/downloads/windows/
    exit /b 1
)

python --version

echo [2/5] Creating virtual environment (.venv)...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        exit /b 1
    )
) else (
    echo .venv already exists. Reusing it.
)

echo [3/5] Activating virtual environment...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    exit /b 1
)

echo [4/5] Installing Audio Engine neural dependencies...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip.
    exit /b 1
)
python -m pip install -e ".[neural]"
if errorlevel 1 (
    echo ERROR: Failed to install project dependencies.
    exit /b 1
)

echo [5/5] Downloading AI models to models\ ...
python tools\download_models.py
if errorlevel 1 (
    echo ERROR: Model download failed.
    exit /b 1
)

echo.
echo Setup complete! Run run.bat to start the audio engine.
exit /b 0
