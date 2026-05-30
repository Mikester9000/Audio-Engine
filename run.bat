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

if "%~1"=="" goto :launch_studio

if /I "%~1"=="studio" (
    shift
    goto :launch_studio
)

if /I "%~1"=="help" goto :show_help
if /I "%~1"=="--help" goto :show_help
if /I "%~1"=="-h" goto :show_help

audio-engine %*
exit /b %errorlevel%

:launch_studio
echo Launching Audio Engine Studio...
audio-engine studio
if errorlevel 1 (
    echo.
    echo WARNING: Studio failed to launch. Showing CLI help instead.
    audio-engine --help
    exit /b 1
)
exit /b 0

:show_help
echo Common commands:
echo   audio-engine list-backends
echo   audio-engine generate-music --prompt "epic orchestral battle theme" --duration 30 --output battle.wav --backend musicgen
echo   audio-engine generate-sfx --prompt "large explosion" --duration 1.5 --output explosion.wav --backend musicgen
echo   audio-engine generate-voice --text "Welcome, hero." --voice narrator --output voice.wav
echo.
audio-engine --help
