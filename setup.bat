@echo off
setlocal

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

echo ============================================================
echo  Audio Engine Setup
echo ============================================================
echo.
echo Choose a setup mode:
echo   1  Manual / procedural only  (no AI models, fastest setup)
echo   2  AI workflow               (installs MusicGen + downloads ~1.5 GB model)
echo.
set /p "SETUP_MODE=Enter 1 or 2 [default: 1]: "
if "%SETUP_MODE%"=="" set "SETUP_MODE=1"
if not "%SETUP_MODE%"=="1" if not "%SETUP_MODE%"=="2" (
    echo Invalid choice. Defaulting to manual-only mode.
    set "SETUP_MODE=1"
)

echo.
echo [1/4] Checking Python installation...
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

echo [2/4] Creating virtual environment (.venv)...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        exit /b 1
    )
) else (
    echo .venv already exists. Reusing it.
)

echo [3/4] Activating virtual environment...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    exit /b 1
)

python -m pip install --upgrade pip >nul 2>&1

if "%SETUP_MODE%"=="1" (
    echo [4/4] Installing core dependencies ^(manual/procedural mode - no AI libraries^)...
    python -m pip install -e "."
    if errorlevel 1 (
        echo ERROR: Failed to install core project dependencies.
        exit /b 1
    )
    echo.
    echo ============================================================
    echo  Setup complete! ^(Manual/Procedural mode^)
    echo ============================================================
    echo.
    echo  Run the studio GUI with:
    echo    audio-engine studio
    echo.
    echo  Or use the CLI directly:
    echo    audio-engine generate-music --prompt "battle theme" --duration 30 --output battle.wav
    echo    audio-engine generate-sfx --prompt "explosion" --duration 1.5 --output boom.wav
    echo.
    echo  No AI model download required in this mode.
    echo  All audio is generated using the built-in procedural synthesizer.
    echo ============================================================
) else (
    echo [4/4] Installing AI dependencies...
    python -m pip install -e ".[neural]"
    if errorlevel 1 (
        echo WARNING: Full neural install failed ^(Kokoro often fails on Windows^).
        echo Retrying with MusicGen-only dependency set...
        python -m pip install -e ".[musicgen]"
        if errorlevel 1 (
            echo ERROR: Failed to install AI project dependencies.
            echo TIP: Try running setup.bat again and choose option 1 ^(manual mode^).
            exit /b 1
        )
    )
    echo.
    echo Downloading MusicGen Medium model ^(~1.5 GB^)...
    echo This may take several minutes. If it stalls, press Ctrl+C and run:
    echo   python tools\download_models.py --skip
    echo Then place the model manually in models\musicgen-medium\
    echo.
    python tools\download_models.py
    if errorlevel 1 (
        echo.
        echo WARNING: Model download incomplete or failed.
        echo You can still use procedural generation without the model.
        echo.
        echo To retry the download later:
        echo   .venv\Scripts\activate.bat
        echo   python tools\download_models.py
        echo.
        echo To use manual model placement, see: models\README.md
    )
    echo.
    echo ============================================================
    echo  Setup complete! ^(AI mode^)
    echo ============================================================
    echo.
    echo  Run the studio GUI with:
    echo    audio-engine studio
    echo.
    echo  Or double-click run.bat to launch the Studio GUI.
    echo ============================================================
)

exit /b 0
