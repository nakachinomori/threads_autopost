"""ドライブから落とした写真を、Threadsに載せられる JPEG に整える。

- HEIC/PNG なども JPEG に変換（Threads は JPEG/PNG のみ対応）
- 長辺 1440px に縮小
- EXIF（撮影場所の GPS など）を全部消す。向きだけは反映してから消す

使い方: python prepare_photo.py 入力ファイル 出力.jpg
必要: pip install pillow pillow-heif
"""

import sys

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()

MAX_SIDE = 1440

src, dst = sys.argv[1], sys.argv[2]
with Image.open(src) as im:
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    clean = Image.new("RGB", im.size)
    clean.paste(im)
    clean.save(dst, "JPEG", quality=88, optimize=True)
print(f"{dst}: {clean.size[0]}x{clean.size[1]}")
