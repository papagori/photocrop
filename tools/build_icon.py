"""Generate the deterministic multi-resolution Windows application icon."""
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'assets' / 'photocrop.ico'


def create_icon(size=256):
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = round(size * 0.07)
    radius = round(size * 0.22)
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=radius,
        fill='#172554',
    )

    line_width = max(2, round(size * 0.065))
    inset = round(size * 0.27)
    arm = round(size * 0.22)
    color = '#60a5fa'
    # Four crop-frame corners; rounded line joins keep small icon sizes legible.
    for points in (
        ((inset, inset + arm), (inset, inset), (inset + arm, inset)),
        ((size - inset - arm, inset), (size - inset, inset), (size - inset, inset + arm)),
        ((inset, size - inset - arm), (inset, size - inset), (inset + arm, size - inset)),
        ((size - inset - arm, size - inset), (size - inset, size - inset),
         (size - inset, size - inset - arm)),
    ):
        draw.line(points, fill=color, width=line_width, joint='curve')
    return image


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    icon = create_icon()
    icon.save(OUTPUT, format='ICO', sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                                          (64, 64), (128, 128), (256, 256)])
    print(OUTPUT)


if __name__ == '__main__':
    main()
