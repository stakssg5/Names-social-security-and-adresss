import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "atr_studio_gui_mock.png")

# Canvas
W, H = 980, 600
img = Image.new("RGB", (W, H), (245, 245, 245))
draw = ImageDraw.Draw(img)
font = ImageFont.load_default()

# Title bar
draw.rectangle([0, 0, W, 40], fill=(30, 136, 229))
draw.text((12, 12), "Atr Zoe Utility", fill=(255, 255, 255), font=font)

# Group: ATR (left)
left_x, top_y, right_x = 16, 56, W//2 - 12
# Group frame
draw.rectangle([left_x, top_y, right_x, H-16], outline=(180,180,180), width=1)
draw.text((left_x+10, top_y-14), "ATR", fill=(0,0,0), font=font)

# Row 0: Reader + Java Card Type + REFRESH
y = top_y + 14
label_color = (30,30,30)
box_color = (255,255,255)
border = (200,200,200)

def box(x, y, w, h):
    draw.rectangle([x, y, x+w, y+h], fill=box_color, outline=border)

# Reader label and combo
draw.text((left_x+12, y+4), "Reader", fill=label_color, font=font)
box(left_x+80, y, 180, 24)
# Java Card Type
draw.text((left_x+270, y+4), "Java Card Type", fill=label_color, font=font)
box(left_x+380, y, 130, 24)
# Refresh button
box(right_x-90, y, 80, 24)
draw.text((right_x-70, y+5), "REFRESH", fill=(0,0,0), font=font)

y += 36
# READ ATR button
box(left_x+12, y, 120, 28)
draw.text((left_x+32, y+7), "READ ATR", fill=(0,0,0), font=font)

y += 40
# ATR display
draw.text((left_x+12, y+4), "ATR", fill=label_color, font=font)
box(left_x+80, y, right_x - (left_x+80) - 12, 56)

y += 72
# Parse tree placeholder
box(left_x+12, y, right_x - (left_x+12) - 12, H - 16 - y - 12)
draw.text((left_x+24, y+8), "Parsed ATR details...", fill=(120,120,120), font=font)

# Group: Customize ATR (right)
rx0 = W//2 + 12
rx1 = W - 16
draw.rectangle([rx0, top_y, rx1, H-16], outline=(180,180,180), width=1)
draw.text((rx0+10, top_y-14), "Customize ATR", fill=(0,0,0), font=font)

ry = top_y + 14
# Choose ATR row
draw.text((rx0+12, ry+4), "Choose ATR", fill=label_color, font=font)
box(rx0+100, ry, rx1 - (rx0+100) - 12, 24)
ry += 36
# Radio buttons
draw.ellipse([rx0+12, ry+4, rx0+24, ry+16], outline=border)
draw.text((rx0+30, ry+2), "Default ATR", fill=label_color, font=font)

draw.ellipse([rx0+130, ry+4, rx0+142, ry+16], outline=border)
draw.text((rx0+148, ry+2), "Custom ATR", fill=label_color, font=font)

draw.ellipse([rx0+250, ry+4, rx0+262, ry+16], outline=border)
draw.text((rx0+268, ry+2), "Known ATR", fill=label_color, font=font)

ry += 28
# Custom hex row
draw.text((rx0+12, ry+4), "Custom hex", fill=label_color, font=font)
box(rx0+100, ry, rx1 - (rx0+100) - 12, 24)
ry += 36
# APDU Script loader row
draw.text((rx0+12, ry+4), "APDU Script", fill=label_color, font=font)
box(rx0+100, ry, rx1 - (rx0+100) - 100, 24)
box(rx1-88, ry, 76, 24)
draw.text((rx1-70, ry+5), "Load...", fill=(0,0,0), font=font)
ry += 32
# Script preview
box(rx0+12, ry, rx1 - (rx0+12) - 12, 110)
draw.text((rx0+24, ry+8), "Script preview", fill=(120,120,120), font=font)
ry += 120
# Buttons row
box(rx0+12, ry, 110, 28)
draw.text((rx0+30, ry+7), "COPY ATR", fill=(0,0,0), font=font)
box(rx0+132, ry, 130, 28)
draw.text((rx0+150, ry+7), "SEND TO CARD", fill=(0,0,0), font=font)
ry += 40
# Ready indicators
draw.text((rx0+12, ry+2), "READER: READY", fill=label_color, font=font)
ry += 20
draw.text((rx0+12, ry+2), "INSERTED CARD: UNKNOWN", fill=label_color, font=font)

img.save(OUT)
print(OUT)
