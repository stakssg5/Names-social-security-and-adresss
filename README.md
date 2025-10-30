ATR Utility

## Modern SmartCard ATR Suite
Transparent, ISO 7816‑compliant smartcard initialization that just works.

### Why
Enough with outdated tooling and opaque docs. We make smartcard tech easy, modern, and transparent.

### Key Capabilities
- ATR (Answer‑To‑Reset) database (4,000+ entries): Instantly recognize and validate cards.
- ISO 7816 compliant: Ensure smartcard reset/initialization meets industry standards.
- Pre‑personalization initialization: Prepare cards reliably before any application load.
- Compatibility checks: Confidently use with X2, Foundry, EMV, or other smartcard apps.
- Easy to use: Clear flows and scripting for APDU operations.
- Read & write with any smartcard reader: Works with common PC/SC devices.
- Affordable price: Safe, trustworthy ATR initialization at a price you’ll love.

### Compatible Smartcards
- JavaCard — J2A040 (and similar JavaCard platforms)
- Broad support for EMV and general smartcard applications

### What You Get
- Consistency: Industry‑standard initialization every time.
- Confidence: Compatibility validation against 4,000+ ATRs.
- Simplicity: Straightforward workflows, clear outputs, and modern tooling.

A lightweight toolset to work with smart‑card ATRs (Answer To Reset). It includes a CLI and a simple desktop GUI that mirrors the screenshots you provided.

CLI features:
- Read ATRs from connected cards via PC/SC (optional, requires system PC/SC and pyscard)
- Parse and validate ATR bytes
- Build simple ATRs for testing/simulation workflows
- Search a small built‑in database of known ATRs

GUI features:
- Reader picker, READ ATR button, live ATR hex display
- Parsed ATR details in a table
- A "Customize ATR" panel with default/custom/known ATR pickers (for analysis/copy)
- "Send to card" placeholder that explains vendor‑specific limitations

Quick start

1) Install Python 3.11+.
2) Install dependencies (no admin privileges required):

```
pip3 install -r requirements.txt
```

Optional: to enable the `read` command, install system PC/SC and pyscard:
- Linux: install `pcscd`, `libpcsclite-dev`, and `swig`, then `pip3 install pyscard`
- macOS: PC/SC is built-in; run `pip3 install pyscard`
- Windows: install an PC/SC driver (e.g., from your reader vendor), then `pip install pyscard`

Usage

Show help:

```
python3 -m atr_utility --help
```

Build a simple ATR (T=1, with TA1 and TC1 and 5 historical bytes):

```
python3 -m atr_utility build --protocol 1 --ta1 11 --tc1 FF --hist 1122334455
```

Parse an ATR:

```
python3 -m atr_utility parse "3B D5 11 FF 01 11 22 33 44 55 2B"
```

Search known ATRs:

```
python3 -m atr_utility db-search 3B9F
```

Read ATR from a card (requires pyscard + PC/SC):

```
python3 -m atr_utility read --reader 0
```

Run the GUI
-----------

```
python3 -m atr_utility.gui
```

Program the card (Send to card)
-------------------------------

Changing a card's ATR is vendor‑specific. The GUI lets you load and run an APDU script and substitutes variables from the parsed/selected ATR so you can use the exact bytes your card requires.

1) Click "Load..." and choose a `.apdu` text script.
2) Pick the ATR (read one, select from DB, or enter custom).
3) Click "SEND TO CARD" to execute the script against the selected reader.

Script format: one APDU per line as hex bytes; `#` starts a comment. The following variables are expanded before sending:

- `{ATR_HEX}`: full ATR with spaces (e.g., `3B 00`)
- `{ATR_NS}`: ATR without spaces
- `{TS}`, `{T0}`, `{K}`: single values
- `{HIST_HEX}`, `{HIST_NS}`: historical bytes
- `{TCK}`, `{COMPUTED_TCK}`: if present; empty otherwise
- `{PROTOCOLS}`: space‑separated protocol values (e.g., `00 01`)

A bundled example exists at `atr_utility/example_script.apdu` (no‑op by default). Replace it with your device/vendor commands.

Build a Windows .exe (optional)
-------------------------------

Option A — one‑command build (recommended)

- CMD:
```
scripts\build_exe.bat
```

- PowerShell:
```
powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
```

This installs PyInstaller (if needed) and produces `dist\Atr Zoe Utility.exe`. It also bundles `atr_utility\example_script.apdu` so the GUI can auto‑load the example script.

Option B — manual command

```
pip install pyinstaller
pyinstaller -F -w -n "Atr Zoe Utility" -i NONE ^
  --hidden-import "PySide6.QtNetwork" ^
  --collect-qt-plugins "tls,networkinformation" ^
  --add-data "atr_utility\example_script.apdu;atr_utility" ^
  -p . atr_utility\gui.py
```

Notes:
- To enable PC/SC card reading on Windows, install your reader's PC/SC driver and `pip install pyscard`.
- PyInstaller bundles required Qt6 DLLs automatically for PySide6. The command above explicitly includes QtNetwork and TLS plugins.

Notes and limitations

- Customizing the ATR on a physical JavaCard/JCOP requires vendor-specific commands and is not standardized. The GUI mirrors the workflow for analysis and copying ATRs, but "Send to card" is intentionally a no‑op unless you add vendor commands.
- The ATR builder included here is intentionally simple (single interface group, optional TA1/TB1/TC1, protocol T=0 or T=1). It computes and appends TCK automatically when needed.

Project layout

- `atr_utility/atr.py`: ATR parsing and builder helpers
- `atr_utility/pcsc.py`: PC/SC reader helpers (optional)
- `atr_utility/cli.py`: CLI entry points
- `atr_utility/atr_db.py`: tiny database of example ATRs
- `atr_utility/gui.py`: desktop GUI (PySide6)

License

MIT