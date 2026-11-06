"""Export the site art as WebP at two widths (for srcset) and build the 1200x630 share card.

Run from the site folder with any Python that has Pillow:
    python tools/optimize_art.py
Writes public/art/<name>-<width>.webp and public/art/share.jpg. The source JPEGs stay put.
"""
from pathlib import Path
from PIL import Image, ImageChops

ART = Path(__file__).resolve().parent.parent / "public" / "art"
QUALITY = 78

# name -> widths. Small one covers phones at 1x/2x, large one covers desktop and 3x phones.
SIZES = {
    "halfcover": (720, 1280),
    "mock-opening-wood": (800, 1600),
    "mock-quadrant-wood": (800, 1600),
    "magical": (800, 1600),
    "hideandseek": (800, 1600),
    "cover": (480, 800),
    "deep": (900, 1800),
}

PAPER = (247, 241, 227)  # --paper in style.css


def export_webp():
    total = 0
    for name, widths in SIZES.items():
        src = Image.open(ART / f"{name}.jpg").convert("RGB")
        for w in widths:
            w = min(w, src.width)
            h = round(src.height * w / src.width)
            out = ART / f"{name}-{w}.webp"
            src.resize((w, h), Image.LANCZOS).save(out, "WEBP", quality=QUALITY, method=6)
            kb = out.stat().st_size / 1024
            total += kb
            print(f"{out.name:32} {w}x{h}  {kb:6.0f} KB")
    print(f"all variants: {total:.0f} KB")


def share_card():
    """Title lettering on the left, Fin on his rock on the right, on the site's paper color."""
    src = Image.open(ART / "halfcover.jpg").convert("RGB")
    W, H = 1200, 630
    card = Image.new("RGB", (W, H), PAPER)

    title = src.crop((470, 50, 930, 410))  # LOOK UP, FIN!
    byline = src.crop((370, 980, 1030, 1120))  # a story about life beyond the screen by EMILY CHEN
    fin = src.crop((330, 460, 1070, 890))  # Fin on the rock

    def fit(img, w):
        return img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)

    title = fit(title, 430)
    byline = fit(byline, 400)
    fin = fit(fin, 620)

    left_cx = 290
    ty = (H - title.height - 24 - byline.height) // 2
    pieces = [
        (title, (left_cx - title.width // 2, ty)),
        (byline, (left_cx - byline.width // 2, ty + title.height + 24)),
        (fin, (W - fin.width - 48, (H - fin.height) // 2 + 30)),
    ]
    for img, pos in pieces:
        # multiply so the white page melts into the paper, same trick as the site
        region = card.crop((*pos, pos[0] + img.width, pos[1] + img.height))
        card.paste(ImageChops.multiply(region, img), pos)

    out = ART / "share.jpg"
    card.save(out, "JPEG", quality=85, optimize=True, progressive=True)
    print(f"{out.name:32} {W}x{H}  {out.stat().st_size / 1024:6.0f} KB")


def deep_tall(extra=160, trim=10):
    """Footer art with the anglerfish lifted: grow the plain water under it.

    The bottom rows of deep.jpg are empty painted water. Append them mirrored,
    then upright again, so both joins are seamless and the fish sits higher
    above the footer rule. The painting itself is untouched, except `trim`
    rows off the very bottom, which are lighter and would show as a line.
    """
    src = Image.open(ART / "deep.jpg").convert("RGB")
    src = src.crop((0, 0, src.width, src.height - trim))
    w, h = src.size
    strip = src.crop((0, h - extra // 2, w, h))
    tall = Image.new("RGB", (w, h + extra))
    tall.paste(src, (0, 0))
    tall.paste(strip.transpose(Image.FLIP_TOP_BOTTOM), (0, h))
    tall.paste(strip, (0, h + extra // 2))
    tall.save(ART / "deep-tall.jpg", "JPEG", quality=82, optimize=True, progressive=True)
    for tw in (900, 1800):
        th = round(tall.height * tw / w)
        out = ART / f"deep-tall-{tw}.webp"
        tall.resize((tw, th), Image.LANCZOS).save(out, "WEBP", quality=QUALITY, method=6)
        print(f"{out.name:32} {tw}x{th}  {out.stat().st_size / 1024:6.0f} KB")


if __name__ == "__main__":
    export_webp()
    share_card()
    deep_tall()
