#!/usr/bin/env python3
"""Generate portrait framing without assuming the artwork follows a uniform grid.

Run with: uv run --with pillow python dashboard/src/avatars/generate-portrait-frames.py
The original gutter boundaries isolate portraits; opaque torso rows determine the
bottom edge. Ignore faint alpha fringe and isolated pixels, retaining one pixel
of antialiasing. Source images are never modified.
"""
import json
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
OPACITY_THRESHOLD = 128
MIN_TORSO_WIDTH_FRACTION = 0.4
metadata = json.loads((HERE / 'crop-metadata.json').read_text())
voices = json.loads((HERE / 'voice-order.json').read_text())
frames = {}
for name in ('editorial', 'matte'):
    sheet = Image.open(HERE.parent / 'assets' / 'voice-avatars' / f'{name}.png').convert('RGBA')
    crop = metadata[name]
    frames[name] = []
    for cell in range(len(voices)):
        row, column = divmod(cell, 6)
        left, right = crop['columns'][row][column:column + 2]
        top, bottom = crop['rows'][row:row + 2]
        alpha = sheet.getchannel('A').crop((left, top, right, bottom))
        width, height = alpha.size
        torso_rows = [y for y in range(height)
                      if sum(alpha.getpixel((x, y)) >= OPACITY_THRESHOLD for x in range(width))
                      >= width * MIN_TORSO_WIDTH_FRACTION]
        bottom = top + min(height, max(torso_rows) + 2)
        frames[name].append({'left': left, 'top': top, 'width': width, 'height': bottom - top})
(HERE / 'portrait-frames.json').write_text(json.dumps(frames, indent=2) + '\n')
