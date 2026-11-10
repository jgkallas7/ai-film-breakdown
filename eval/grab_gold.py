"""Full-size frame(s) from a gold-test work dir, optional zoom crop.

    python3 -P grab_gold.py <work> <endzone|wide> <clip> <t> [<t> ...] [--crop x0,y0,x1,y1] [--zoom 2]

Crop box is in source pixels (1920x1080). Prints the jpg paths to Read.
"""
import argparse, os, subprocess
from pathlib import Path
import imageio_ffmpeg
from PIL import Image

FF = imageio_ffmpeg.get_ffmpeg_exe()
ap = argparse.ArgumentParser()
ap.add_argument("work"); ap.add_argument("angle"); ap.add_argument("clip", type=int); ap.add_argument("t", type=float, nargs="+")
ap.add_argument("--crop"); ap.add_argument("--zoom", type=float, default=1.0)
a = ap.parse_args()
mp4 = Path(a.work) / a.angle / f"Clip {a.clip:03d}.mp4"
outdir = Path(a.work) / "grabs"; outdir.mkdir(exist_ok=True)
for t in a.t:
    # Readers A and B share this folder. The crop box AND the zoom are in the name, and the frame is written to a
    # private temp file first, so neither reader ever opens the other's crop or a half-written image.
    tag = (('_' + a.crop.replace(',', '-')) if a.crop else '') + (f"_z{a.zoom:g}" if a.zoom != 1 else '')
    out = outdir / f"c{a.clip:03d}_{a.angle[:2]}_{t:05.2f}{tag}.jpg"
    tmp = outdir / f".tmp_{os.getpid()}_{out.name}"
    subprocess.run([FF, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(mp4), "-frames:v", "1", "-q:v", "2", str(tmp)], check=True)
    if a.crop or a.zoom != 1:
        im = Image.open(tmp)
        if a.crop:
            im = im.crop(tuple(int(float(v)) for v in a.crop.split(",")))
        if a.zoom != 1:
            im = im.resize((int(im.width * a.zoom), int(im.height * a.zoom)), Image.LANCZOS)
        im.save(tmp, format="JPEG", quality=92)
    os.replace(tmp, out)
    print(out)
