"""Computer-vision front measurement (run with ~/.venvs/cv/bin/python).

    ~/.venvs/cv/bin/python cv_front.py <workdir> <clip:set_t> [<clip:set_t> ...] --def-color white --off-color purple
        [--angle tight|wide] [--out <workdir>/cv]

For each clip:
 1. snap = first sustained motion jump after set_t (Tight clip, 10 fps energy); frames at snap-0.4 (SET), +0.4, +0.8, +1.3
 2. YOLO person boxes; team by torso colour (white / purple / other)
 3. yard lines (white lines on green, Hough) -> depth axis + px per yard; LOS through the offense's front line
 4. each defender: depth off the ball (yds), technique vs the 5 OL (0,1,2i,2,3,4i,4,5,7/9, wide),
    stance (hand down vs standing, from box height), and post-snap move (rush / drop / hold) vs the nearest yard line
Writes <out>/cNNN.json and <out>/cNNN_set.jpg (numbered overlay) + cNNN_strip.jpg (set and 3 post-snap frames).
It MEASURES, it doesn't decide: readers and Coach check the overlay. Built 10/6/2026 for OPA.

STATUS 10/6: detection + team colour + numbered overlay + snap strip work. The yard-line measurement (depth / technique /
post-snap move in yards) did NOT work on foggy OPA film (2 or 0 lines found; depths nonsense), so it's off by default
(--measure turns it on). Readers make the alignment calls from the overlay + strip. Real depth needs a field homography
from clean yard lines/hashes; revisit on clear-weather film.
"""
import argparse, json, math, subprocess
from pathlib import Path
import cv2, numpy as np
import imageio_ffmpeg
from ultralytics import YOLO

FF = imageio_ffmpeg.get_ffmpeg_exe()


def frame(mp4, t):
    p = subprocess.run([FF, "-v", "error", "-ss", f"{max(t, 0):.2f}", "-i", str(mp4), "-frames:v", "1",
                        "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    return cv2.imdecode(np.frombuffer(p.stdout, np.uint8), cv2.IMREAD_COLOR)


def snap_after(mp4, t0):
    W, H, fps = 192, 108, 10
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{max(t0 - 1, 0):.2f}", "-t", "6", "-i", str(mp4),
                          "-vf", f"fps={fps},scale={W}:{H},format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)
    if len(fr) < 15:
        return t0 + 0.8
    e = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    e = np.convolve(e, np.ones(3) / 3, mode="same")
    start = 10                                            # index of t0
    base = np.median(e[max(0, start - 8):start + 2])
    for i in range(start, len(e) - 6):
        if (e[i:i + 6] > max(base * 1.8, base + 0.8)).mean() > .8:
            return max(t0 - 1, 0) + i / fps
    return t0 + 0.8


def team_of(img, b):
    x0, y0, x1, y1 = map(int, b)
    h = y1 - y0
    torso = img[y0 + int(.18 * h):y0 + int(.5 * h), x0 + int(.2 * (x1 - x0)):x1 - int(.2 * (x1 - x0))]
    if torso.size == 0:
        return "other"
    hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(float)
    v_ref = team_of.v_ref if hasattr(team_of, "v_ref") else 155     # set per frame in predict loop (dusk film)
    white = ((hsv[:, 1] < 45) & (hsv[:, 2] > v_ref)).mean()
    # fog washes purple toward grey-blue: hue 100-170, low saturation is still purple if it isn't white
    purple = ((hsv[:, 0] > 100) & (hsv[:, 0] < 170) & (hsv[:, 1] > 22) & (hsv[:, 2] > 30) & (hsv[:, 2] < 230)).mean()
    dark = (hsv[:, 2] < 70).mean()
    if purple > .2 and purple > white * 0.8:
        return "purple"
    if white > .35:
        return "white"
    if dark > .5:
        return "dark"
    return "other"


def yard_lines(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = ((hsv[..., 1] < 60) & (hsv[..., 2] > 170)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    L = cv2.HoughLinesP(mask, 1, np.pi / 360, 80, minLineLength=img.shape[0] // 4, maxLineGap=40)
    if L is None:
        return None
    segs = [tuple(map(float, l)) for l in np.asarray(L).reshape(-1, 4)]
    ang = np.array([math.atan2(y1 - y0, x1 - x0) % math.pi for x0, y0, x1, y1 in segs])
    length = np.array([math.hypot(x1 - x0, y1 - y0) for x0, y0, x1, y1 in segs])
    # dominant long-line direction = yard lines (sidelines/hashes are rarer and far shorter in the Tight view)
    hist, edges = np.histogram(ang, bins=36, range=(0, math.pi), weights=length)
    k = hist.argmax()
    th = (edges[k] + edges[k + 1]) / 2
    keep = [s for s, a in zip(segs, ang) if abs(((a - th + math.pi / 2) % math.pi) - math.pi / 2) < math.radians(6)]
    d = np.array([math.cos(th), math.sin(th)])            # along the yard line
    n = np.array([-d[1], d[0]])                           # across yard lines = depth axis
    offs = sorted(np.dot(np.array([(x0 + x1) / 2, (y0 + y1) / 2]), n) for x0, y0, x1, y1 in keep)
    # merge segments of the same line, then the median gap between neighbouring lines = 5 yds
    lines = []
    for o in offs:
        if not lines or o - lines[-1][-1] > 25:
            lines.append([o])
        else:
            lines[-1].append(o)
    pos = [float(np.mean(g)) for g in lines]
    gaps = [b - a for a, b in zip(pos, pos[1:]) if b - a > 40]
    if not gaps:
        return None
    return {"d": d.tolist(), "n": n.tolist(), "lines": pos, "px_per_yd": float(np.median(gaps)) / 5}


def tech_name(x, ol):
    """x and ol (5 OL lateral coords, left->right from the camera) in px; returns tech + side."""
    c = ol[2]
    w = np.median(np.diff(ol)) if len(ol) > 1 else 60
    rel = (x - c) / w                                      # in OL-widths from the center
    side = "L" if rel < 0 else "R"
    a = abs(rel)
    for lim, t in ((.2, "0"), (.55, "1"), (.8, "2i"), (1.2, "2"), (1.45, "3"), (1.75, "4i"), (2.2, "4"),
                   (2.6, "5"), (3.3, "7/9")):
        if a < lim:
            return t, ("" if t == "0" else side)
    return "wide", side


def analyse(model, mp4, set_t, defc, offc):
    snap = snap_after(mp4, set_t)
    ts = {"set": snap - 0.4, "p04": snap + 0.4, "p08": snap + 0.8, "p13": snap + 1.3}
    imgs = {k: frame(mp4, t) for k, t in ts.items()}
    img = imgs["set"]
    res = model.predict(img, imgsz=1920, conf=0.25, classes=[0], verbose=False)[0]
    boxes = [b.tolist() for b in res.boxes.xyxy.cpu().numpy()]
    P = [{"box": b, "team": team_of(img, b), "foot": [(b[0] + b[2]) / 2, b[3]], "h": b[3] - b[1]} for b in boxes]
    yl = yard_lines(img)
    out = {"snap_t": round(snap, 2), "set_t": round(ts["set"], 2), "n_people": len(P), "yl": yl}
    D = [p for p in P if p["team"] == defc]
    O = [p for p in P if p["team"] == offc]
    out["n_def"], out["n_off"] = len(D), len(O)
    if not yl or len(O) < 3 or not D:
        out["error"] = "no yard lines or too few players found"
        return out, imgs, P
    d, n, ppy = np.array(yl["d"]), np.array(yl["n"]), yl["px_per_yd"]
    for p in P:
        f = np.array(p["foot"])
        p["depth_px"], p["lat_px"] = float(f @ n), float(f @ d)
    # which way is the defense? defenders' median depth vs offense's
    sgn = 1 if np.median([p["depth_px"] for p in D]) > np.median([p["depth_px"] for p in O]) else -1
    # LOS = offense's front edge: median of the 7 offensive players closest to the defense
    # LOS = front edge of the offense: OL are the offensive players CLOSEST to the defense, so take the
    # 2nd-nearest (robust to one mis-coloured box) and nudge half a yard toward the D (OL feet sit behind the ball)
    od = sorted((p["depth_px"] * sgn for p in O), reverse=True)
    los = (od[min(1, len(od) - 1)] + 0.5 * ppy) * sgn
    # OL = the 5 offensive players nearest the LOS and the lateral middle of that group
    front = [p for p in O if abs(p["depth_px"] - los) < 2.0 * ppy]
    if len(front) < 5:
        front = sorted(O, key=lambda p: abs(p["depth_px"] - los))[:5]
    mid = np.median([p["lat_px"] for p in front])
    ol = sorted(sorted(front, key=lambda p: abs(p["lat_px"] - mid))[:5], key=lambda p: p["lat_px"])
    ol_x = [p["lat_px"] for p in ol]
    stand_h = np.median([p["h"] for p in P]) if P else 1
    defs = []
    for i, p in enumerate(sorted(D, key=lambda p: p["lat_px"]), 1):
        depth = (p["depth_px"] - los) * sgn / ppy
        t, side = tech_name(p["lat_px"], ol_x)
        defs.append({"id": i, "depth_yd": round(depth, 1), "tech": t, "side": side,
                     "stance": "down" if p["h"] < 0.78 * stand_h else "up",
                     "box": [round(v) for v in p["box"]], "foot": [round(v) for v in p["foot"]],
                     "on_line": depth < 1.6})
    out["ol_lat"] = [round(x) for x in ol_x]
    out["los_px"], out["sgn"] = round(los), sgn
    out["defenders"] = defs
    # post-snap: re-detect, match each on-line / near-line defender, measure depth change vs the yard lines
    later = {}
    for k in ("p04", "p08", "p13"):
        r = model.predict(imgs[k], imgsz=1920, conf=0.25, classes=[0], verbose=False)[0]
        yk = yard_lines(imgs[k])
        bs = [b.tolist() for b in r.boxes.xyxy.cpu().numpy()]
        later[k] = [(b, team_of(imgs[k], b)) for b in bs], yk
    for dd in defs:
        if dd["depth_yd"] > 4.5:
            continue
        moves = []
        prev = np.array(dd["foot"], float)
        prev_ref = yl
        for k in ("p04", "p08", "p13"):
            cand, yk = later[k]
            cand = [((b[0] + b[2]) / 2, b[3]) for b, tm in cand if tm == defc]
            if not cand or not yk:
                break
            c = min(cand, key=lambda f: math.hypot(f[0] - prev[0], f[1] - prev[1]))
            if math.hypot(c[0] - prev[0], c[1] - prev[1]) > 4 * ppy:
                break
            # depth relative to the nearest yard line, in yards, comparable across frames even if the camera pans
            def rel(f, y):
                nn = np.array(y["n"]); o = np.dot(f, nn)
                near = min(y["lines"], key=lambda L: abs(L - o))
                return (o - near) / y["px_per_yd"]
            moves.append(rel(np.array(c), yk) - rel(prev, prev_ref))
            prev, prev_ref = np.array(c), yk
        tot = sum(m for m in moves if abs(m) < 3) * sgn          # + = deeper (away from the LOS) = drop
        dd["post_move_yd"] = round(tot, 1) if moves else None
        dd["post"] = None if not moves else ("drop" if tot > 1.0 else "rush" if tot < -0.8 else "hold/flow")
    return out, imgs, P


def overlay(img, out, P, defc, path):
    im = img.copy()
    for p in P:
        col = {"white": (255, 255, 255), "purple": (200, 60, 160), "dark": (40, 40, 40)}.get(p["team"], (0, 200, 255))
        x0, y0, x1, y1 = map(int, p["box"])
        cv2.rectangle(im, (x0, y0), (x1, y1), col, 2)
    if not out.get("measured"):
        for i, p in enumerate(sorted([p for p in P if p["team"] == defc], key=lambda p: p["box"][0]), 1):
            x0, y0 = int(p["box"][0]), int(p["box"][1])
            cv2.putText(im, f"D{i}", (x0, y0 - 8), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 5)
            cv2.putText(im, f"D{i}", (x0, y0 - 8), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.imwrite(str(path), im, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return
    for dd in out.get("defenders", []):
        x0, y0, x1, y1 = dd["box"]
        lab = f"{dd['id']}:{dd['tech']}{dd['side']} {dd['depth_yd']}y {dd['stance']}" + (f" {dd['post']}" if dd.get("post") else "")
        cv2.putText(im, lab, (x0 - 10, y0 - 8), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 0, 0), 4)
        cv2.putText(im, lab, (x0 - 10, y0 - 8), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 255, 255), 2)
    for x in out.get("ol_lat", []):                       # mark OL along the LOS
        d, n = np.array(out["yl"]["d"]), np.array(out["yl"]["n"])
        pt = d * x + n * out["los_px"]
        cv2.circle(im, (int(pt[0]), int(pt[1])), 9, (0, 0, 255), -1)
    cv2.imwrite(str(path), im, [cv2.IMWRITE_JPEG_QUALITY, 85])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work"); ap.add_argument("clips", nargs="+")
    ap.add_argument("--def-color", default="white"); ap.add_argument("--off-color", default="purple")
    ap.add_argument("--measure", action="store_true", help="experimental yard-line measurements (unreliable in fog)")
    ap.add_argument("--angle", default="tight"); ap.add_argument("--out"); ap.add_argument("--model", default="yolo11x.pt")
    a = ap.parse_args()
    work = Path(a.work); out_dir = Path(a.out or work / "cv"); out_dir.mkdir(exist_ok=True)
    model = YOLO(a.model)
    for item in a.clips:
        parts = item.split(":")                      # clip:set_t  or  clip:set_t:snap_t (reader-corrected snap)
        c, t = int(parts[0]), float(parts[1])
        forced = float(parts[2]) if len(parts) > 2 else None
        mp4 = work / ("clips_tight" if a.angle == "tight" else "clips") / f"Clip {c:03d}.mp4"
        if a.measure:
            out, imgs, P = analyse(model, mp4, t, a.def_color, a.off_color); out["measured"] = True
        else:
            snap = forced if forced is not None else snap_after(mp4, t)
            ts = {"set": snap - 0.4, "p04": snap + 0.4, "p08": snap + 0.8, "p13": snap + 1.3}
            imgs = {k: frame(mp4, v) for k, v in ts.items()}
            v = cv2.cvtColor(imgs["set"], cv2.COLOR_BGR2HSV)[..., 2]
            team_of.v_ref = min(155, float(np.percentile(v, 75)) + 25)    # grey-at-dusk whites still beat the turf
            r = model.predict(imgs["set"], imgsz=1920, conf=0.25, classes=[0], verbose=False)[0]
            P = [{"box": b.tolist(), "team": team_of(imgs["set"], b.tolist())} for b in r.boxes.xyxy.cpu().numpy()]
            out = {"snap_t": round(snap, 2), "set_t": round(ts["set"], 2), "n_def": sum(p["team"] == a.def_color for p in P),
                   "n_off": sum(p["team"] == a.off_color for p in P),
                   "def_boxes": [[round(v) for v in p["box"]] for p in sorted([p for p in P if p["team"] == a.def_color], key=lambda p: p["box"][0])]}
        out["clip"] = c
        (out_dir / f"c{c:03d}.json").write_text(json.dumps(out, indent=1))
        overlay(imgs["set"], out, P, a.def_color, out_dir / f"c{c:03d}_set.jpg")
        strip = [cv2.resize(imgs[k], (960, 540)) for k in ("set", "p04", "p08", "p13")]
        for k, im in zip(("SET", "+0.4", "+0.8", "+1.3"), strip):
            cv2.putText(im, f"#{c} {k}", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 3)
        cv2.imwrite(str(out_dir / f"c{c:03d}_strip.jpg"),
                    np.vstack([np.hstack(strip[:2]), np.hstack(strip[2:])]), [cv2.IMWRITE_JPEG_QUALITY, 80])
        print(c, "snap", out["snap_t"], "def boxes", out.get("n_def"), "off boxes", out.get("n_off"), out.get("error", ""))


if __name__ == "__main__":
    main()
