"""Full-res frame(s) from an extracted clip, optional zoom crop.

    python3 grab.py <workdir> <clip> <t> [<t> ...] [--crop x0,y0,x1,y1] [--zoom 2] [--tight | --angle endzone]

Crop box is in source pixels (1920x1080 on most Hudl film). Prints the jpg paths to Read.
Angles: the default is the Wide angle (`clips/`); `--tight` is the Tight angle (`clips_tight/`); `--angle <name>` is
any other angle make_sheets.py unpacked (`<workdir>/<name>/`, e.g. endzone).
"""
import argparse, os, subprocess
from pathlib import Path
import imageio_ffmpeg
from PIL import Image

FF = imageio_ffmpeg.get_ffmpeg_exe()
ap = argparse.ArgumentParser()
ap.add_argument("work"); ap.add_argument("clip", type=int); ap.add_argument("t", type=float, nargs="+")
ap.add_argument("--crop"); ap.add_argument("--zoom", type=float, default=1.0)
ap.add_argument("--tight", action="store_true", help="use the Tight (end-zone/close) angle if the zip had one")
ap.add_argument("--angle", help="any other angle folder in the work dir (endzone, ...)")
a = ap.parse_args()
folder = a.angle or ("clips_tight" if a.tight else "clips")
mp4 = Path(a.work) / folder / f"Clip {a.clip:03d}.mp4"
if not mp4.exists():
    have = sorted(p.name for p in Path(a.work).iterdir() if p.is_dir() and any(p.glob("Clip *.mp4")))
    raise SystemExit(f"no {mp4}. Angle folders in this work dir: {', '.join(have) or 'none'}")
outdir = Path(a.work) / "grabs"; outdir.mkdir(exist_ok=True)
ang = f"_{a.angle[:2]}" if a.angle else ("T" if a.tight else "")
for t in a.t:
    # The crop box and zoom are in the name, and each frame goes to a private temp file first. Two readers work the
    # same clips at once (blind pairs): with one shared name per clip + time, one reader's crop replaced the other's,
    # or was opened half-written (OPQ 10/24, reader opr-b2).
    tag = (f"_crop{a.crop.replace(',', '-')}" if a.crop else "") + (f"_z{a.zoom:g}" if a.zoom != 1 else "")
    out = outdir / f"c{a.clip:03d}{ang}_{t:05.1f}{tag}.jpg"
    tmp = outdir / f".tmp_{os.getpid()}_{out.name}"
    subprocess.run([FF, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(mp4), "-frames:v", "1", str(tmp)], check=True)
    if a.crop or a.zoom != 1:
        im = Image.open(tmp)
        if a.crop:
            im = im.crop(tuple(int(float(v)) for v in a.crop.split(",")))
        if a.zoom != 1:
            im = im.resize((int(im.width * a.zoom), int(im.height * a.zoom)), Image.LANCZOS)
        im.save(tmp, format="JPEG", quality=90)
    os.replace(tmp, out)
    print(out)
