"""Full-res frame(s) from an extracted clip, optional zoom crop.

    python3 grab.py <workdir> <clip> <t> [<t> ...] [--crop x0,y0,x1,y1] [--zoom 2]

Crop box is in 1920x1080 source pixels. Prints the jpg paths to Read.
"""
import argparse, subprocess
from pathlib import Path
import imageio_ffmpeg
from PIL import Image

FF = imageio_ffmpeg.get_ffmpeg_exe()
ap = argparse.ArgumentParser()
ap.add_argument("work"); ap.add_argument("clip", type=int); ap.add_argument("t", type=float, nargs="+")
ap.add_argument("--crop"); ap.add_argument("--zoom", type=float, default=1.0)
ap.add_argument("--tight", action="store_true", help="use the Tight (end-zone/close) angle if the zip had one")
a = ap.parse_args()
mp4 = Path(a.work) / ("clips_tight" if a.tight else "clips") / f"Clip {a.clip:03d}.mp4"
outdir = Path(a.work) / "grabs"; outdir.mkdir(exist_ok=True)
for t in a.t:
    out = outdir / f"c{a.clip:03d}{'T' if a.tight else ''}_{t:05.1f}{'_crop' if a.crop else ''}.jpg"
    subprocess.run([FF, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(mp4), "-frames:v", "1", str(out)], check=True)
    if a.crop or a.zoom != 1:
        im = Image.open(out)
        if a.crop:
            im = im.crop(tuple(int(v) for v in a.crop.split(",")))
        if a.zoom != 1:
            im = im.resize((int(im.width * a.zoom), int(im.height * a.zoom)), Image.LANCZOS)
        im.save(out, quality=90)
    print(out)
