"""Timeline strip for picking the set frame by eye: one stamped frame per second across the whole clip.

    python3 snap_strip.py <workdir> <clip> [<clip> ...] [--step 1.0] [--tight]

Writes <workdir>/strips/cNNN.jpg (4 columns, field band only) and prints the detector's guess
(snap_frame.snap_time) as a hint. The detector alone is NOT trusted: on OPA clip 55 (28 s long) it picked
1.2 s while players were still walking up; the real set was about 10-11 s. Readers pick set_t from the
strip: the LAST frame where everyone is still (one legal motion man allowed) right before the ball moves,
then confirm with grab.py at set_t and set_t + 1 (the +1 frame must show the play under way).
"""
import argparse, subprocess, tempfile
from pathlib import Path
import imageio_ffmpeg
from PIL import Image, ImageDraw
import snap_frame as sf

FF = imageio_ffmpeg.get_ffmpeg_exe()
ap = argparse.ArgumentParser()
ap.add_argument("work"); ap.add_argument("clips", type=int, nargs="+")
ap.add_argument("--step", type=float, default=1.0); ap.add_argument("--tight", action="store_true")
a = ap.parse_args()
out = Path(a.work) / "strips"; out.mkdir(exist_ok=True)
for c in a.clips:
    mp4 = Path(a.work) / ("clips_tight" if a.tight else "clips") / f"Clip {c:03d}.mp4"
    with tempfile.TemporaryDirectory() as td:
        subprocess.run([FF, "-v", "error", "-i", str(mp4), "-vf", f"fps={1 / a.step},scale=480:-1",
                        f"{td}/f%03d.jpg"], check=True)
        frames = sorted(Path(td).glob("f*.jpg"))
        tiles = []
        for i, f in enumerate(frames):
            im = Image.open(f).convert("RGB")
            w, h = im.size
            im = im.crop((0, int(h * .12), w, int(h * .62)))          # field band: line of scrimmage + backfield
            d = ImageDraw.Draw(im)
            d.rectangle((0, 0, 92, 22), fill=(0, 0, 0)); d.text((4, 4), f"#{c} t={i * a.step:.0f}s", fill=(255, 255, 0))
            tiles.append(im)
    if not tiles:
        print(c, "no frames"); continue
    tw, th = tiles[0].size; cols = 4; rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (tw * cols, th * rows))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * tw, (i // cols) * th))
    jpg = out / f"c{c:03d}{'T' if a.tight else ''}.jpg"; sheet.save(jpg, quality=80)
    print(c, "detector_hint", sf.snap_time(sf.energy(Path(a.work) / "clips" / f"Clip {c:03d}.mp4")), jpg)
