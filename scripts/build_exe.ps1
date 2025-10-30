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

# Build GUI executable and include example_script.apdu in atr_utility package
& pyinstaller -F -w -n "Atr Zoe Utility" -i NONE --add-data "atr_utility\example_script.apdu;atr_utility" -p . atr_utility\gui.py
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "Build complete. See dist\Atr Zoe Utility.exe"
Write-Host "If it fails to start, ensure your PC/SC driver is installed and pyscard is available."
