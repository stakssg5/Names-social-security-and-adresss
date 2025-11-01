Param(
  [string]$Python = "python"
)

# Verify Python
& $Python --version | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Error "Python not found in PATH. Install Python 3.11+ and retry."
  exit 1
}

# Install dependencies
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit 1 }
& $Python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit 1 }
& $Python -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) { exit 1 }

# Build ATR Utility GUI executable and include example_script.apdu in atr_utility package
& pyinstaller -F -w -n "Atr Zoe Utility" -i NONE `
  --hidden-import "PySide6.QtNetwork" `
  --collect-qt-plugins "tls,networkinformation" `
  --add-data "atr_utility\example_script.apdu;atr_utility" `
  -p . atr_utility\gui.py
if ($LASTEXITCODE -ne 0) { exit 1 }

# Build Crypto PR+ GUI executable (Telegram mini app clone)
& pyinstaller -F -w -n "Crypto PR+" -i NONE -p . crypto_pr_plus\gui.py
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "Build complete. See dist\Atr Zoe Utility.exe and dist\Crypto PR+.exe"
Write-Host "If the ATR build fails to start, ensure your PC/SC driver is installed and pyscard is available."
