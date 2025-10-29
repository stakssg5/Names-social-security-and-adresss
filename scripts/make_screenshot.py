#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont


def render_image(text: str, title: str, output_path: str) -> None:
    padding = 18
    header_height = 44
    bg = (11, 15, 20)  # dark
    header_bg = (17, 26, 38)
    title_fg = (136, 192, 208)  # cyan-ish
    text_fg = (216, 222, 233)   # near-white

    font = ImageFont.load_default()

    # Measure text block
    tmp = Image.new("RGB", (10, 10))
    d = ImageDraw.Draw(tmp)
    bbox = d.multiline_textbbox((0, 0), text, font=font, spacing=4)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    width = max(880, text_w + padding * 2)
    height = header_height + text_h + padding * 2

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle((0, 0, width, header_height), fill=header_bg)
    draw.text((padding, (header_height - 12) // 2), title, fill=title_fg, font=font)

    # Body
    draw.multiline_text((padding, header_height + padding - 8), text, fill=text_fg, font=font, spacing=4)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)


def main() -> None:
    ap = argparse.ArgumentParser(description="Render a command's output to a PNG screenshot")
    ap.add_argument("--cmd", required=True, help="Shell command to execute")
    ap.add_argument("--title", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    try:
        proc = subprocess.run(args.cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out_text = proc.stdout.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError as e:
        out_text = (e.stdout or b"").decode("utf-8", errors="replace")

    full_text = f"$ {args.cmd}\n" + out_text
    render_image(full_text, args.title, args.output)


if __name__ == "__main__":
    main()
