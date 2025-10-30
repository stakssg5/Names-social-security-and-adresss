import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
README = os.path.join(ROOT, "README.md")
OUT = os.path.join(ROOT, "manual_screenshot.png")

# Read README content
with open(README, "r", encoding="utf-8") as f:
    content = f.read()

# Keep first N characters to avoid overly tall images
MAX_CHARS = 4000
content = content[:MAX_CHARS]

# Wrap text to a fixed width
wrap_width = 100
lines = []
for para in content.splitlines():
    if para.strip() == "":
        lines.append("")
        continue
    lines.extend(textwrap.wrap(para, width=wrap_width))

# Basic rendering parameters
padding = 20
line_height = 18
width = 1200
height = padding * 2 + line_height * max(1, len(lines))

# Create image
img = Image.new("RGB", (width, height), color=(245, 245, 245))
draw = ImageDraw.Draw(img)

# Try to use a monospaced font if available
font = ImageFont.load_default()

# Title bar
title = "ATR Utility Manual (README.md excerpt)"
draw.rectangle([(0, 0), (width, 40)], fill=(33, 150, 243))
draw.text((padding, 10), title, fill=(255, 255, 255), font=font)

# Render text
y = 50
text_color = (20, 20, 20)
for line in lines:
    draw.text((padding, y), line, fill=text_color, font=font)
    y += line_height

img.save(OUT)
print(OUT)
