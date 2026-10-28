"""Find the snap in a clip from motion energy; save the pre-snap (set) frame.

    python3 snap_frame.py <workdir> <clip> [<clip> ...] [--lead 0.6] [--out DIR]

Snap = start of the first sustained jump in frame-to-frame motion after the
opening seconds (players set -> everyone moves). Set frame = snap - lead.
Prints  clip  snap_t  set_jpg  (snap_t = -1 when no clear jump: pick by eye).
Check a few by eye per game; panning cameras can fool it.
"""
import argparse, subprocess
from pathlib import Path
import numpy as np, imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 192, 108, 10


def energy(mp4):
    raw = subprocess.run([FF, "-v", "error", "-i", str(mp4), "-vf", f"fps={FPS},scale={W}:{H},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)
    band = fr[:, int(H * .25):int(H * .9)]                  # field band, skip sky / near bench heads
    return np.abs(np.diff(band, axis=0)).mean(axis=(1, 2))


def snap_time(e):
    if len(e) < 20:
        return -1
    k = np.convolve(e, np.ones(3) / 3, mode="same")
    base = np.percentile(k[: max(10, len(k) // 3)], 30)
    thr = max(base * 2.2, base + 1.0)
    for i in range(5, len(k) - 5):                          # need 1s of sustained motion
        if (k[i:i + 10] > thr).mean() > .8 and k[i - 3:i].mean() < thr:
            return i / FPS
    return -1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("work"); ap.add_argument("clips", type=int, nargs="+")
    ap.add_argument("--lead", type=float, default=0.6); ap.add_argument("--out")
    a = ap.parse_args()
    out = Path(a.out or Path(a.work) / "set"); out.mkdir(parents=True, exist_ok=True)
    for c in a.clips:
        mp4 = Path(a.work) / "clips" / f"Clip {c:03d}.mp4"
        t = snap_time(energy(mp4))
        jpg = out / f"c{c:03d}_set.jpg"
        if t >= 0:
            subprocess.run([FF, "-v", "error", "-y", "-ss", f"{max(t - a.lead, 0):.2f}", "-i", str(mp4),
                            "-frames:v", "1", str(jpg)], check=True)
        print(c, t, jpg if t >= 0 else "-")
