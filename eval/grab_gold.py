"""Full-size frame(s) from a gold-test work dir, optional zoom crop.

    python3 -P grab_gold.py <work> <endzone|wide> <clip> <t> [<t> ...] [--crop x0,y0,x1,y1] [--zoom 2]

Crop box is in source pixels (1920x1080). Prints the jpg paths to Read.
"""
import argparse, subprocess
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
    tag = ('_' + a.crop.replace(',', '-')) if a.crop else ''
    out = outdir / f"c{a.clip:03d}_{a.angle[:2]}_{t:05.2f}{tag}.jpg"
    subprocess.run([FF, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(mp4), "-frames:v", "1", "-q:v", "2", str(out)], check=True)
    if a.crop or a.zoom != 1:
        im = Image.open(out)
        if a.crop:
            im = im.crop(tuple(int(float(v)) for v in a.crop.split(",")))
        if a.zoom != 1:
            im = im.resize((int(im.width * a.zoom), int(im.height * a.zoom)), Image.LANCZOS)
        im.save(out, quality=92)
    print(out)
