ATR Utility

A lightweight, cross-platform command‑line tool to work with smart‑card ATRs (Answer To Reset):
- Read ATRs from connected cards via PC/SC (optional, requires system PC/SC and pyscard)
- Parse and validate ATR bytes
- Build simple ATRs for testing/simulation workflows
- Search a small built‑in database of known ATRs

This repository contains only a CLI for now. A GUI can be added later if needed.

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

Notes and limitations

- Customizing the ATR on a physical JavaCard/JCOP requires vendor-specific commands and is not standardized. This tool focuses on reading, parsing, and constructing ATR byte strings for analysis and testing.
- The ATR builder included here is intentionally simple (single interface group, optional TA1/TB1/TC1, protocol T=0 or T=1). It computes and appends TCK automatically when needed.

Project layout

- `atr_utility/atr.py`: ATR parsing and builder helpers
- `atr_utility/pcsc.py`: PC/SC reader helpers (optional)
- `atr_utility/cli.py`: CLI entry points
- `atr_utility/atr_db.py`: tiny database of example ATRs

License

MIT