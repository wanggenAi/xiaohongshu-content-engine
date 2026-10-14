"""Render original 3:4 information cards from reviewed JSON (requires Pillow)."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def render(source: Path, destination: Path, font_path: str):
    cards = json.loads(source.read_text(encoding="utf-8"))
    destination.mkdir(parents=True, exist_ok=True)
    previews = []
    for index, card in enumerate(cards, 1):
        dark = index in {1, 4}
        background, ink = ("#162B2B", "#FFF8E9") if dark else ("#FFF8E9", "#162B2B")
        accent = "#E4AE60" if dark else "#AC5236"
        canvas = Image.new("RGB", (1200, 1600), background)
        draw = ImageDraw.Draw(canvas)

        def text(x, y, value, size=56, fill=ink, draw=draw, index=index):
            font = ImageFont.truetype(font_path, size)
            if draw.textbbox((x, y), value, font=font)[2] > 1100:
                raise ValueError(f"card {index}: text overflows: {value}")
            draw.text((x, y), value, font=font, fill=fill)

        draw.rectangle((92, 110, 180, 120), fill=accent)
        text(92, 160, card["kicker"], 40, accent)
        y = 275
        for line in card["title"]:
            text(88, y, line, 108)
            y += 142
        y += 100
        for block in card["blocks"]:
            draw.rounded_rectangle((88, y, 1110, y + 180), radius=25, outline=accent, width=3)
            text(118, y + 28, block[0], 54, accent)
            text(118, y + 100, block[1], 43)
            y += 220
        if y > 1420:
            raise ValueError(f"card {index}: content extends into footer")
        text(92, 1460, card["footer"], 32)
        text(1010, 1460, f"{index:02d}/04", 32, accent)
        canvas.save(destination / f"{index:02d}.png")
        previews.append(canvas.resize((360, 480)))
    contact = Image.new("RGB", (1440, 480), "white")
    for i, preview in enumerate(previews):
        contact.paste(preview, (360 * i, 0))
    # Keep the contact sheet out of the upload folder so only story pages are selected.
    contact.save(destination.parent / "preview.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--font", default="/System/Library/Fonts/STHeiti Medium.ttc")
    args = parser.parse_args()
    render(args.source, args.destination, args.font)
