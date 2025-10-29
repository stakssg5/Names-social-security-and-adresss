from __future__ import annotations

import os
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from .atr import parse_atr, to_hex, build_simple_atr
from .pcsc import list_readers, connect_and_get_atr
from .atr_db import search_known_atrs

console = Console()


@click.group(help="ATR Utility: read, parse, build, and search ATRs")
@click.version_option()
def atr() -> None:
    pass


@atr.command("read", help="Read ATR from a connected smart card via PC/SC")
@click.option("--reader", "reader_id", help="Reader index or name substring")
def cmd_read(reader_id: Optional[str]) -> None:
    rid: Optional[int | str] = None
    if reader_id is not None:
        if reader_id.isdigit():
            rid = int(reader_id)
        else:
            rid = reader_id
    readers = list_readers()
    if not readers:
        console.print("[red]No PC/SC readers found or pyscard missing[/red]")
        return
    try:
        name, atr_bytes = connect_and_get_atr(rid)
    except Exception as exc:  # pragma: no cover
        console.print(f"[red]Failed to read card:[/red] {exc}")
        return

    console.print(f"Reader: [bold]{name}[/bold]")
    console.print(f"ATR: [bold]{to_hex(atr_bytes)}[/bold]")

    res = parse_atr(atr_bytes)
    _print_parse_result(res)


@atr.command("parse", help="Parse an ATR hex string or file path to bytes")
@click.argument("input_value", metavar="HEX_OR_FILE")
def cmd_parse(input_value: str) -> None:
    data: bytes
    if os.path.isfile(input_value):
        data = open(input_value, "rb").read()
    else:
        data = bytes.fromhex(input_value.replace(" ", "").replace("-", ""))
    res = parse_atr(data)
    _print_parse_result(res)


@atr.command("build", help="Build a simple ATR")
@click.option("--protocol", type=click.Choice(["0", "1"], case_sensitive=False), default="0")
@click.option("--ts", default="3B", help="Initial character (TS) in hex, default 3B")
@click.option("--ta1", default=None, help="TA1 byte in hex (optional)")
@click.option("--tb1", default=None, help="TB1 byte in hex (optional)")
@click.option("--tc1", default=None, help="TC1 byte in hex (optional)")
@click.option("--hist", default="", help="Historical bytes as hex (0..15 bytes)")
def cmd_build(protocol: str, ts: str, ta1: Optional[str], tb1: Optional[str], tc1: Optional[str], hist: str) -> None:
    def hx(x: Optional[str]) -> Optional[int]:
        if x is None or x == "":
            return None
        return int(x, 16)

    out = build_simple_atr(
        ts=int(ts, 16),
        protocol=int(protocol),
        historical_bytes=hist,
        ta1=hx(ta1),
        tb1=hx(tb1),
        tc1=hx(tc1),
    )
    console.print(f"Built ATR: [bold]{out.hex(' ').upper()}[/bold]")


@atr.command("db-search", help="Search a small known ATR database")
@click.argument("query")
def cmd_db(query: str) -> None:
    matches = search_known_atrs(query)
    if not matches:
        console.print("No matches.")
        return
    table = Table(title="Known ATRs")
    table.add_column("ATR")
    table.add_column("Description")
    for atr_hex, desc in matches:
        table.add_row(atr_hex, desc)
    console.print(table)


def _print_parse_result(res):  # type: ignore[no-untyped-def]
    table = Table(title="ATR Parse Result")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("TS", f"0x{res.ts:02X}")
    table.add_row("T0", f"0x{res.t0:02X}")
    table.add_row("Historical bytes (K)", str(res.k))
    table.add_row("Protocols", ", ".join([f"T={p}" for p in res.protocols]))
    table.add_row("Historical", res.historical_bytes.hex(" ").upper())
    if res.tck is not None:
        table.add_row("TCK", f"0x{res.tck:02X} (computed 0x{res.computed_tck:02X}) -> {'OK' if res.tck_valid else 'BAD'}")

    for group in res.interface_bytes:
        for key, val in group.items():
            table.add_row(key, f"0x{val:02X}")

    console.print(table)


if __name__ == "__main__":
    atr()
