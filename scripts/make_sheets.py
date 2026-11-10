"""Hudl game zip -> one labeled contact sheet per clip (for frame-reader agents).

    python3 make_sheets.py "<game.zip>" <workdir> [--frames 6] [--width 1568]

Writes  <workdir>/clips/Clip NNN.mp4   (the Wide angle; extracted once; reused by grab.py)
        <workdir>/clips_tight/         (the Tight angle, when the zip has one)
        <workdir>/<angle>/             (any other angle in the zip, e.g. endzone: "End Zone - Clip NNN.mp4")
        <workdir>/sheets/cNNN.jpg      (2-col grid, frames evenly spaced 5%..97%,
                                        each tile stamped with clip # and t=seconds)
        <workdir>/clips.json           (clip -> duration seconds)
Work in the session scratchpad -- never unpack film into a synced folder.
"""
import argparse, json, re, shutil, subprocess, sys, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

FF = imageio_ffmpeg.get_ffmpeg_exe()


def duration(mp4):
    err = subprocess.run([FF, "-i", str(mp4)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def frame(mp4, t, w):
    p = subprocess.run([FF, "-v", "error", "-ss", f"{t:.2f}", "-i", str(mp4), "-frames:v", "1",
                        "-vf", f"scale={w}:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                       capture_output=True)
    from io import BytesIO
    return Image.open(BytesIO(p.stdout)).convert("RGB")


def sheet(args):
    clip, mp4, out, n, width = args
    d = duration(mp4)
    ts = [d * (0.05 + 0.92 * i / (n - 1)) for i in range(n)]
    tw = width // 2
    tiles = [frame(mp4, t, tw) for t in ts]
    th = tiles[0].height
    img = Image.new("RGB", (tw * 2, th * ((n + 1) // 2)), "black")
    font = ImageFont.load_default(size=22)
    for i, (t, im) in enumerate(zip(ts, tiles)):
        dr = ImageDraw.Draw(im)
        dr.rectangle([0, 0, 190, 30], fill="black")
        dr.text((6, 3), f"#{clip} t={t:.1f}s", fill="yellow", font=font)
        img.paste(im, ((i % 2) * tw, (i // 2) * th))
    img.save(out, quality=82)
    return clip, round(d, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("zip"); ap.add_argument("work")
    ap.add_argument("--frames", type=int, default=6); ap.add_argument("--width", type=int, default=1568)
    a = ap.parse_args()
    work = Path(a.work); (work / "clips").mkdir(parents=True, exist_ok=True); (work / "sheets").mkdir(exist_ok=True)
    zf = zipfile.ZipFile(a.zip)
    jobs, angles = [], {}
    for name in zf.namelist():
        m = re.match(r"(?:.*/)?(.+?) - Clip (\d+)\.mp4$", name)
        if not m:
            continue
        ang, clip = m.group(1).lower().replace(" ", ""), int(m.group(2))
        # Wide -> clips/ (the sheets), Tight -> clips_tight/ (grab.py --tight); any other angle Hudl exported
        # (End Zone, a drone ...) -> <work>/<angle>/ for grab.py / snap_strip.py --angle <angle>.
        folder = {"wide": "clips", "tight": "clips_tight"}.get(ang, ang)
        angles[folder] = angles.get(folder, 0) + 1
        mp4 = work / folder / f"Clip {clip:03d}.mp4"
        if not mp4.exists() or mp4.stat().st_size != zf.getinfo(name).file_size:
            mp4.parent.mkdir(exist_ok=True)
            with zf.open(name) as src, open(mp4, "wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 22)
        if folder == "clips":
            jobs.append((clip, mp4, work / "sheets" / f"c{clip:03d}.jpg", a.frames, a.width))
    if not jobs:
        print(f"NO 'Wide - Clip NNN.mp4' in this zip, so no sheets were built. Angles found: {angles or 'none'}. "
              f"Read from the strips instead: snap_strip.py <work> <clips> --angle <one of those folders>.")
    with ThreadPoolExecutor(8) as ex:
        durs = dict(ex.map(sheet, sorted(jobs)))
    (work / "clips.json").write_text(json.dumps(durs, indent=0))
    print(f"{len(durs)} clips -> {work/'sheets'}  (angle folders: {angles})")

if __name__ == "__main__":
    sys.exit(main())
