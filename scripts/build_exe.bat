@echo off
setlocal

REM Optional: choose Python executable
if not defined PYTHON set PYTHON=python

%PYTHON% --version >nul 2>&1
if errorlevel 1 (
  echo Python not found in PATH. Install Python 3.11+ and retry.
  exit /b 1
)

REM Upgrade pip and install dependencies
%PYTHON% -m pip install --upgrade pip || exit /b 1
%PYTHON% -m pip install -r requirements.txt || exit /b 1
%PYTHON% -m pip install pyinstaller || exit /b 1

REM Build ATR Utility GUI executable; bundle example_script.apdu into atr_utility package
pyinstaller -F -w -n "Atr Zoe Utility" -i NONE ^
  --hidden-import "PySide6.QtNetwork" ^
  --collect-qt-plugins "tls,networkinformation" ^
  --add-data "atr_utility\example_script.apdu;atr_utility" ^
  -p . atr_utility\gui.py || exit /b 1

REM Build Crypto PR+ GUI executable (Telegram mini app clone)
pyinstaller -F -w -n "Crypto PR+" -i NONE ^
  -p . crypto_pr_plus\gui.py || exit /b 1

echo.
echo Build complete. See dist\Atr Zoe Utility.exe and dist\Crypto PR+.exe
echo If the ATR build fails to start, ensure your PC/SC driver is installed and pyscard is available.
endlocal
