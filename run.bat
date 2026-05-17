@echo off
setlocal

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv was not found.
    echo Please run setup.bat first.
    exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate .venv.
    echo Please run setup.bat again.
    exit /b 1
)

echo Audio Engine is ready in offline mode.
echo.
echo Common commands:
echo   audio-engine list-backends
echo   audio-engine generate-music --prompt "epic orchestral battle theme" --duration 30 --output battle.wav --backend musicgen
echo   audio-engine generate-sfx --prompt "large explosion" --duration 1.5 --output explosion.wav --backend audiogen
echo   audio-engine generate-voice --text "Welcome, hero." --voice narrator --output voice.wav --backend kokoro
echo.
audio-engine --help
