"""One-off asset build: turn the supplied SENTINEL logo sheet into app assets.

Crops the primary mark from the brand sheet and emits transparent PNGs plus
favicons. Kept in the repo so the assets are reproducible rather than opaque
binaries. Run: python scripts/build_logo_assets.py
"""

from pathlib import Path

from PIL import Image

SRC = Path(__file__).resolve().parent / "sentinel-logo-sheet.jpg"
OUT = Path(__file__).resolve().parent.parent / "frontend" / "public"

# Bounding box of the primary mark on the brand sheet, with a little padding.
CROP = (585, 131, 822, 428)

EMERALD = (52, 211, 153)
LIGHT_INK = (241, 245, 249)
DARK_INK = (15, 23, 42)
DEEP_BG = (11, 15, 18)

# Ink coverage is derived from how far a pixel sits from the sheet's white
# background. WHITE_FLOOR ignores JPEG ringing around the strokes, and
# ALPHA_CUTOFF drops the faint speckles it still leaves behind.
WHITE_FLOOR = 232.0
INK_SPAN = 150.0
ALPHA_CUTOFF = 0.28


def is_greenish(r: int, g: int, b: int) -> bool:
    return g > r + 15 and g > b + 8 and g < 215


def recolor(src: Image.Image, ink: tuple[int, int, int]) -> Image.Image:
    """Flatten the sheet's white background to alpha; recolor ink, keep the gem."""
    src = src.convert("RGB")
    out = Image.new("RGBA", src.size, (0, 0, 0, 0))
    src_px = src.load()
    out_px = out.load()
    width, height = src.size
    for y in range(height):
        for x in range(width):
            r, g, b = src_px[x, y]
            alpha = (WHITE_FLOOR - min(r, g, b)) / INK_SPAN
            alpha = max(0.0, min(1.0, alpha))
            if alpha < ALPHA_CUTOFF:
                continue  # JPEG ringing, not ink
            color = EMERALD if is_greenish(r, g, b) else ink
            out_px[x, y] = (*color, round(alpha * 255))
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mark = Image.open(SRC).crop(CROP)

    # Square canvas so the mark never distorts when scaled in the UI.
    def squared(img: Image.Image) -> Image.Image:
        side = max(img.size)
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
        return canvas.resize((512, 512), Image.LANCZOS)

    light_on_dark = squared(recolor(mark, LIGHT_INK))
    dark_on_light = squared(recolor(mark, DARK_INK))
    emerald_only = squared(recolor(mark, EMERALD))

    light_on_dark.save(OUT / "sentinel-mark.png")
    dark_on_light.save(OUT / "sentinel-mark-dark.png")

    # Favicons: emerald ink reads on both light and dark browser chrome.
    for size in (16, 32):
        emerald_only.resize((size, size), Image.LANCZOS).save(OUT / f"favicon-{size}x{size}.png")
    emerald_only.resize((48, 48), Image.LANCZOS).save(OUT / "favicon.ico", sizes=[(48, 48)])

    # Apple touch icon needs an opaque background.
    touch = Image.new("RGBA", (180, 180), (*DEEP_BG, 255))
    inner = light_on_dark.resize((132, 132), Image.LANCZOS)
    touch.paste(inner, (24, 24), inner)
    touch.convert("RGB").save(OUT / "apple-touch-icon.png")

    print("wrote:", *(p.name for p in sorted(OUT.glob("sentinel-mark*.png"))))
    print("favicons regenerated in", OUT)


if __name__ == "__main__":
    main()
