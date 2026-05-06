@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM Veaja — Windows build script
REM Produces: dist\veaja-1.1.0-windows-x64\veaja.exe
REM           dist\veaja-1.1.0-windows-x64.zip
REM
REM Requirements:
REM   - Python 3.10+ with venv at .\venv
REM   - Run from the VeaJa-TTSsystem folder
REM
REM Usage:
REM   build_windows.bat
REM ─────────────────────────────────────────────────────────────────────────────

setlocal
set VERSION=1.1.0
set OUTPUT=veaja-%VERSION%-windows-x64

echo =^> Activating venv...
call venv\Scripts\activate.bat

echo =^> Installing PyInstaller...
pip install pyinstaller --quiet

echo =^> Cleaning previous build...
if exist build rmdir /s /q build
if exist dist\%OUTPUT% rmdir /s /q dist\%OUTPUT%
if exist dist\%OUTPUT%.zip del /q dist\%OUTPUT%.zip

echo =^> Building veaja.exe...
pyinstaller ^
  --name "veaja" ^
  --windowed ^
  --noconfirm ^
  --clean ^
  --add-data "assets;assets" ^
  --add-data "styles;styles" ^
  --add-data "i18n;i18n" ^
  --add-data "config;config" ^
  --hidden-import "pynput.keyboard._win32" ^
  --hidden-import "pynput.mouse._win32" ^
  --hidden-import "pyttsx3.drivers" ^
  --hidden-import "pyttsx3.drivers.sapi5" ^
  --hidden-import "PyQt6.QtSvg" ^
  --hidden-import "edge_tts" ^
  --hidden-import "pygame.mixer" ^
  --icon "assets\veaja.ico" ^
  main.py

echo =^> Renaming output folder...
cd dist
rename veaja %OUTPUT%
cd ..

echo =^> Creating ZIP...
powershell -Command "Compress-Archive -Path 'dist\%OUTPUT%' -DestinationPath 'dist\%OUTPUT%.zip' -Force"

echo.
echo Done!
echo.
echo   Folder: dist\%OUTPUT%\
echo   ZIP:    dist\%OUTPUT%.zip
echo.
echo   To run: dist\%OUTPUT%\veaja.exe
echo.
echo   NOTE: Windows SmartScreen may warn on first run.
echo   Users should click 'More info' then 'Run anyway'.
echo   Or right-click veaja.exe ^> Properties ^> Unblock.

endlocal
