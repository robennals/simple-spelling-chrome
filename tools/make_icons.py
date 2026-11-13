#!/usr/bin/env python3
"""Draw the extension icons (extension/icons/icon{16,32,48,128}.png).

A rounded blue square with a white "S". Drawn large and scaled down so the
small sizes stay smooth. Needs Pillow and a bold system font (macOS default).

Usage: make_icons.py [FONT_PATH]
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = sys.argv[1] if len(sys.argv) > 1 else "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
OUT = Path(__file__).resolve().parent.parent / "extension" / "icons"
BLUE = (37, 99, 235, 255)
BIG = 512

img = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle((16, 16, BIG - 16, BIG - 16), radius=110, fill=BLUE)
font = ImageFont.truetype(FONT, 380)
box = draw.textbbox((0, 0), "S", font=font)
x = (BIG - (box[2] - box[0])) / 2 - box[0]
y = (BIG - (box[3] - box[1])) / 2 - box[1]
draw.text((x, y), "S", font=font, fill="white")

OUT.mkdir(parents=True, exist_ok=True)
for size in (16, 32, 48, 128):
    img.resize((size, size), Image.LANCZOS).save(OUT / f"icon{size}.png")
    print(OUT / f"icon{size}.png")
