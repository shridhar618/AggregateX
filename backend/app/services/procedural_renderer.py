"""Offline procedural facial-composite renderer.

One geometry model, two outputs:
  * SVG  – crisp, fast; used for the live editor preview
  * PNG  – Pillow, 3x supersampled then downscaled; used for saving and export

Both outputs are produced from the same primitive list, so the saved PNG always
matches what the operator saw. Rendering is deterministic: the same profile
always produces the same image (textures use a seed derived from the profile).

Honesty rules: unknown traits are drawn with a neutral default and reported in
``notes``; traits the monochrome renderer cannot show (eye colour, skin tone)
are reported as "recorded only". Hair that was never described is drawn as a
dashed "unspecified" outline instead of an invented hairstyle.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import random
from dataclasses import dataclass, field
from typing import Optional

from PIL import Image, ImageChops, ImageDraw, ImageFont

from ..catalog import TRAIT_BY_KEY, option_label
from ..schemas import Mark, Profile

W, H = 600, 750           # logical canvas
CX = W / 2
OUT_SCALE = 1.5           # PNG output = 900 x 1125
SUPERSAMPLE = 3           # internal oversampling for anti-aliasing

PAPER = "#f2f0ea"
SKIN = "#fbfaf6"
INK = "#262626"
SOFT = "#6b6b6b"
SHIRT = "#e4e1da"

HAIR_TONES = {
    "black": "#1b1b1b", "dark": "#2a2a2a", "brown": "#46423e", "red": "#56504b",
    "blonde": "#a09a90", "light": "#a09a90", "gray": "#9b9b9b", "white": "#cdcbc6",
}
DEFAULT_HAIR_TONE = "#4d4d4d"

Point = tuple[float, float]


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def catmull_rom(points: list[Point], closed: bool = False) -> list[tuple[Point, Point, Point, Point]]:
    """Uniform Catmull-Rom spline through ``points`` as cubic Bézier segments."""
    n = len(points)
    if n < 2:
        return []
    segs = []
    count = n if closed else n - 1
    for i in range(count):
        p0 = points[(i - 1) % n] if (closed or i > 0) else points[i]
        p1 = points[i]
        p2 = points[(i + 1) % n]
        p3 = points[(i + 2) % n] if (closed or i + 2 < n) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        segs.append((p1, c1, c2, p2))
    return segs


def bezier_point(seg, t: float) -> Point:
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = seg
    mt = 1 - t
    a, b, c, d = mt ** 3, 3 * mt * mt * t, 3 * mt * t * t, t ** 3
    return (a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3)


def sample_segments(segs) -> list[Point]:
    pts: list[Point] = []
    for seg in segs:
        approx = math.dist(seg[0], seg[1]) + math.dist(seg[1], seg[2]) + math.dist(seg[2], seg[3])
        n = max(4, min(60, int(approx / 3)))
        start = 0 if not pts else 1
        for k in range(start, n + 1):
            pts.append(bezier_point(seg, k / n))
    return pts


def mirror(points: list[Point]) -> list[Point]:
    return [(2 * CX - x, y) for x, y in points]


def point_in_poly(x: float, y: float, poly: list[Point]) -> bool:
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi:
            inside = not inside
        j = i
    return inside


def hex_rgba(color: str, alpha: float = 1.0) -> tuple[int, int, int, int]:
    c = color.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), max(0, min(255, round(alpha * 255))))


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------
@dataclass
class Prim:
    kind: str                         # path | ellipse | rect | text | clip
    pts: list[Point] = field(default_factory=list)        # polyline/polygon points (pre-sampled)
    segs: list = field(default_factory=list)              # bezier segments (for crisp SVG)
    closed: bool = False
    fill: Optional[str] = None
    stroke: Optional[str] = None
    width: float = 1.0
    alpha: float = 1.0
    dash: Optional[tuple[float, float]] = None
    cx: float = 0.0
    cy: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    text: str = ""
    size: float = 11.0
    anchor: str = "start"
    children: list["Prim"] = field(default_factory=list)  # for clip groups
    clip: list[Point] = field(default_factory=list)


class Scene:
    def __init__(self):
        self.prims: list[Prim] = []

    def smooth(self, points: list[Point], closed=False, **style) -> Prim:
        segs = catmull_rom(points, closed)
        p = Prim("path", pts=sample_segments(segs), segs=segs, closed=closed, **style)
        self.prims.append(p)
        return p

    def bezier(self, segs, closed=False, **style) -> Prim:
        p = Prim("path", pts=sample_segments(segs), segs=list(segs), closed=closed, **style)
        self.prims.append(p)
        return p

    def poly(self, points: list[Point], closed=True, **style) -> Prim:
        p = Prim("path", pts=list(points), closed=closed, **style)
        self.prims.append(p)
        return p

    def line(self, a: Point, b: Point, **style) -> Prim:
        return self.poly([a, b], closed=False, **style)

    def ellipse(self, cx, cy, rx, ry, **style) -> Prim:
        p = Prim("ellipse", cx=cx, cy=cy, rx=rx, ry=ry, **style)
        self.prims.append(p)
        return p

    def text(self, x, y, text, size=11, fill=SOFT, anchor="start") -> Prim:
        p = Prim("text", cx=x, cy=y, text=text, size=size, fill=fill, anchor=anchor)
        self.prims.append(p)
        return p

    def clip_group(self, clip: list[Point]) -> "Scene":
        sub = Scene()
        p = Prim("clip", clip=clip, children=sub.prims)
        self.prims.append(p)
        return sub


# ---------------------------------------------------------------------------
# Output: SVG
# ---------------------------------------------------------------------------
def _f(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


def _svg_path_d(p: Prim) -> str:
    if p.segs:
        d = [f"M{_f(p.segs[0][0][0])} {_f(p.segs[0][0][1])}"]
        for _, c1, c2, e in p.segs:
            d.append(f"C{_f(c1[0])} {_f(c1[1])} {_f(c2[0])} {_f(c2[1])} {_f(e[0])} {_f(e[1])}")
    else:
        d = [f"M{_f(p.pts[0][0])} {_f(p.pts[0][1])}"] + [f"L{_f(x)} {_f(y)}" for x, y in p.pts[1:]]
    if p.closed:
        d.append("Z")
    return "".join(d)


def _svg_style(p: Prim) -> str:
    attrs = [f'fill="{p.fill}"' if p.fill else 'fill="none"']
    if p.stroke:
        attrs.append(f'stroke="{p.stroke}" stroke-width="{_f(p.width)}" stroke-linecap="round" stroke-linejoin="round"')
        if p.dash:
            attrs.append(f'stroke-dasharray="{_f(p.dash[0])} {_f(p.dash[1])}"')
    if p.alpha < 1:
        attrs.append(f'opacity="{p.alpha:.2f}"')
    return " ".join(attrs)


def _svg_prims(prims: list[Prim], out: list[str], defs: list[str], counter: list[int]):
    for p in prims:
        if p.kind == "path" and len(p.pts) >= 2:
            out.append(f'<path d="{_svg_path_d(p)}" {_svg_style(p)}/>')
        elif p.kind == "ellipse":
            out.append(f'<ellipse cx="{_f(p.cx)}" cy="{_f(p.cy)}" rx="{_f(p.rx)}" ry="{_f(p.ry)}" {_svg_style(p)}/>')
        elif p.kind == "text":
            anchor = {"start": "start", "end": "end", "middle": "middle"}[p.anchor]
            txt = p.text.replace("&", "&amp;").replace("<", "&lt;")
            out.append(
                f'<text x="{_f(p.cx)}" y="{_f(p.cy)}" font-family="ui-monospace, Menlo, monospace" '
                f'font-size="{_f(p.size)}" letter-spacing="1" fill="{p.fill}" text-anchor="{anchor}">{txt}</text>'
            )
        elif p.kind == "clip":
            counter[0] += 1
            cid = f"c{counter[0]}"
            pts = " ".join(f"{_f(x)},{_f(y)}" for x, y in p.clip)
            defs.append(f'<clipPath id="{cid}"><polygon points="{pts}"/></clipPath>')
            out.append(f'<g clip-path="url(#{cid})">')
            _svg_prims(p.children, out, defs, counter)
            out.append("</g>")


def to_svg(scene: Scene, title: str) -> str:
    body: list[str] = []
    defs: list[str] = []
    _svg_prims(scene.prims, body, defs, [0])
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">'
        f"<title>{safe_title}</title><defs>{''.join(defs)}</defs>{''.join(body)}</svg>"
    )


# ---------------------------------------------------------------------------
# Output: PNG (Pillow)
# ---------------------------------------------------------------------------
def _dash_polyline(pts: list[Point], on: float, off: float) -> list[list[Point]]:
    dashes, cur, drawing, remaining = [], [pts[0]], True, on
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        seg = math.dist((x0, y0), (x1, y1))
        pos = 0.0
        while seg - pos > remaining:
            pos += remaining
            t = pos / seg
            pt = (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
            if drawing:
                cur.append(pt)
                dashes.append(cur)
            else:
                cur = [pt]
            drawing = not drawing
            remaining = on if drawing else off
        remaining -= seg - pos
        if drawing:
            cur.append((x1, y1))
    if drawing and len(cur) > 1:
        dashes.append(cur)
    return dashes


_FONT_CACHE: dict[int, ImageFont.ImageFont] = {}


def _font(px: int):
    if px not in _FONT_CACHE:
        try:
            _FONT_CACHE[px] = ImageFont.load_default(size=px)
        except Exception:  # pragma: no cover - very old Pillow
            _FONT_CACHE[px] = ImageFont.load_default()
    return _FONT_CACHE[px]


def _composite(img: Image.Image, layer: Image.Image, x: int, y: int):
    """alpha_composite ``layer`` at (x, y), clipped to the bounds of ``img``."""
    sx0, sy0 = max(0, -x), max(0, -y)
    dx0, dy0 = max(0, x), max(0, y)
    w = min(layer.width - sx0, img.width - dx0)
    h = min(layer.height - sy0, img.height - dy0)
    if w <= 0 or h <= 0:
        return
    img.alpha_composite(layer.crop((sx0, sy0, sx0 + w, sy0 + h)), (dx0, dy0))


def _draw_prims(img: Image.Image, prims: list[Prim], k: float, ox: float = 0, oy: float = 0):
    draw = ImageDraw.Draw(img, "RGBA")

    def tr(pts):
        return [((x * k) - ox, (y * k) - oy) for x, y in pts]

    for p in prims:
        if p.kind == "path" and len(p.pts) >= 2:
            pts = tr(p.pts)
            if p.fill and p.closed and len(pts) >= 3:
                draw.polygon(pts, fill=hex_rgba(p.fill, p.alpha))
            if p.stroke:
                w = max(1, round(p.width * k))
                line_pts = pts + ([pts[0]] if p.closed else [])
                runs = _dash_polyline(line_pts, p.dash[0] * k, p.dash[1] * k) if p.dash else [line_pts]
                if p.alpha < 1:
                    # Overlapping segment joints would accumulate alpha; draw opaque, fade once.
                    xs = [x for x, _ in line_pts]
                    ys = [y for _, y in line_pts]
                    pad = w + 2
                    bx0, by0 = math.floor(min(xs) - pad), math.floor(min(ys) - pad)
                    bx1, by1 = math.ceil(max(xs) + pad), math.ceil(max(ys) + pad)
                    layer = Image.new("RGBA", (max(1, bx1 - bx0), max(1, by1 - by0)), (0, 0, 0, 0))
                    ld = ImageDraw.Draw(layer)
                    col = hex_rgba(p.stroke, 1.0)
                    for run in runs:
                        if len(run) >= 2:
                            shifted = [(x - bx0, y - by0) for x, y in run]
                            ld.line(shifted, fill=col, width=w, joint="curve")
                            if w >= 3 and not p.closed:
                                r = w / 2
                                for ex, ey in (shifted[0], shifted[-1]):
                                    ld.ellipse([ex - r, ey - r, ex + r, ey + r], fill=col)
                    layer.putalpha(layer.getchannel("A").point(lambda v: round(v * p.alpha)))
                    _composite(img, layer, bx0, by0)
                    draw = ImageDraw.Draw(img, "RGBA")
                    continue
                col = hex_rgba(p.stroke, p.alpha)
                for run in runs:
                    if len(run) >= 2:
                        draw.line(run, fill=col, width=w, joint="curve")
                        if w >= 3 and not p.closed:
                            r = w / 2
                            for ex, ey in (run[0], run[-1]):
                                draw.ellipse([ex - r, ey - r, ex + r, ey + r], fill=col)
        elif p.kind == "ellipse":
            x0, y0 = p.cx * k - p.rx * k - ox, p.cy * k - p.ry * k - oy
            x1, y1 = p.cx * k + p.rx * k - ox, p.cy * k + p.ry * k - oy
            draw.ellipse(
                [x0, y0, x1, y1],
                fill=hex_rgba(p.fill, p.alpha) if p.fill else None,
                outline=hex_rgba(p.stroke, p.alpha) if p.stroke else None,
                width=max(1, round(p.width * k)) if p.stroke else 0,
            )
        elif p.kind == "text":
            font = _font(round(p.size * k))
            anchor = {"start": "ls", "end": "rs", "middle": "ms"}[p.anchor]
            draw.text((p.cx * k - ox, p.cy * k - oy), p.text, fill=hex_rgba(p.fill), font=font, anchor=anchor)
        elif p.kind == "clip":
            xs = [x for x, _ in p.clip]
            ys = [y for _, y in p.clip]
            bx0, by0 = math.floor(min(xs) * k) - 2, math.floor(min(ys) * k) - 2
            bx1, by1 = math.ceil(max(xs) * k) + 2, math.ceil(max(ys) * k) + 2
            layer = Image.new("RGBA", (bx1 - bx0, by1 - by0), (0, 0, 0, 0))
            _draw_prims(layer, p.children, k, bx0, by0)
            mask = Image.new("L", layer.size, 0)
            ImageDraw.Draw(mask).polygon([(x * k - bx0, y * k - by0) for x, y in p.clip], fill=255)
            alpha = ImageChops.multiply(layer.getchannel("A"), mask)
            layer.putalpha(alpha)
            _composite(img, layer, bx0 - round(ox), by0 - round(oy))
            draw = ImageDraw.Draw(img, "RGBA")


def to_png(scene: Scene) -> bytes:
    k = SUPERSAMPLE * OUT_SCALE
    big = Image.new("RGBA", (round(W * k), round(H * k)), hex_rgba(PAPER))
    _draw_prims(big, scene.prims, k)
    out = big.convert("RGB").resize((round(W * OUT_SCALE), round(H * OUT_SCALE)), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Parameter resolution (profile -> drawing parameters + honest notes)
# ---------------------------------------------------------------------------
NEUTRAL = {
    "face_shape": "oval", "jawline": "average", "chin": "rounded", "eye_shape": "almond",
    "eye_spacing": "average", "eyebrow_thickness": "medium", "eyebrow_shape": "straight",
    "nose_shape": "straight", "mouth_shape": None, "ears": "average", "hairline": "normal",
    "hair_style": "straight", "hair_length": "short",
}


@dataclass
class RenderResult:
    svg: str
    scene: Scene
    notes: list[dict]
    seed: int

    _png: Optional[bytes] = None

    @property
    def png(self) -> bytes:
        if self._png is None:
            self._png = to_png(self.scene)
        return self._png


class _Params:
    def __init__(self, profile: Profile):
        self.profile = profile
        self.notes: list[dict] = []
        self.adj = {k: float(v) for k, v in profile.adjustments.items()}

    def a(self, key: str) -> float:
        return self.adj.get(key, 0.0)

    def t(self, key: str, *, default_note: bool = True) -> Optional[str]:
        tv = self.profile.traits.get(key)
        value = tv.value if tv else None
        if value is None and default_note and key in NEUTRAL and NEUTRAL[key] is not None:
            conflict = bool(tv and tv.alternatives)
            label = TRAIT_BY_KEY[key]["label"]
            msg = (f"{label}: conflicting statements ({', '.join(option_label(key, v) for v in tv.alternatives)}). "
                   f"Drawn with a neutral default until resolved.") if conflict else \
                  f"{label}: not described. Drawn with a neutral default ({option_label(key, NEUTRAL[key])})."
            self.notes.append({"trait": key, "kind": "conflict" if conflict else "default", "message": msg})
        return value


def _profile_seed(profile: Profile) -> int:
    payload = json.dumps(profile.model_dump(exclude={"observations"}), sort_keys=True, default=str)
    return int(hashlib.sha256(payload.encode()).hexdigest()[:12], 16)


# ---------------------------------------------------------------------------
# The composite
# ---------------------------------------------------------------------------
def render_profile(profile: Profile, caption: Optional[str] = None) -> RenderResult:
    P = _Params(profile)
    seed = _profile_seed(profile)
    rng = random.Random(seed)
    s = Scene()

    age = P.t("age_range", default_note=False)
    pres = P.t("presentation", default_note=False)
    face = P.t("face_shape") or NEUTRAL["face_shape"]
    jawline = P.t("jawline") or NEUTRAL["jawline"]
    chin = P.t("chin") or NEUTRAL["chin"]

    # --- core proportions -------------------------------------------------
    Wc = 112 * (1 + 0.12 * P.a("face_width"))
    Wc += {"round": 6, "square": 4, "long": -8, "diamond": 5, "triangular": -3}.get(face, 0)
    L = 400 * (1 + 0.08 * P.a("face_length"))
    L += {"long": 30, "round": -16, "square": -6, "heart": -4}.get(face, 0)
    if age == "child":
        L -= 30
        Wc -= 6
    top = 160 - (L - 400) * 0.25
    T = Wc * {"oval": 0.88, "round": 0.92, "square": 0.95, "long": 0.86, "heart": 0.99,
              "diamond": 0.78, "triangular": 0.80}.get(face, 0.88)
    J = Wc * {"oval": 0.78, "round": 0.86, "square": 0.95, "long": 0.76, "heart": 0.62,
              "diamond": 0.68, "triangular": 0.97}.get(face, 0.78)
    J += Wc * {"narrow": -0.08, "wide": 0.08, "angular": 0.04}.get(jawline, 0)
    if pres == "feminine":
        J -= Wc * 0.04
    J += Wc * 0.12 * P.a("jaw_width")
    C = {"pointed": 12, "rounded": 28, "square": 42, "cleft": 32, "receding": 24, "prominent": 33}[chin]
    chin_y = top + L + 14 * P.a("chin_length") + {"prominent": 8, "receding": -6, "pointed": 6}.get(chin, 0)

    eye_y = top + 0.46 * L + 14 * P.a("eye_height")
    if age == "child":
        eye_y += 14
    eye_shape = P.t("eye_shape") or NEUTRAL["eye_shape"]
    spacing = P.t("eye_spacing") or NEUTRAL["eye_spacing"]
    S = 50 * {"close": 0.88, "average": 1.0, "wide": 1.13}[spacing] + 7 * P.a("eye_spacing")
    ew = 23 * (1 + 0.15 * P.a("eye_size")) * (1.08 if age == "child" else 1)
    eh = {"almond": 9, "round": 12.5, "narrow": 6, "hooded": 8.5, "downturned": 9, "upturned": 9,
          "deep_set": 8.5}[eye_shape] * (1 + 0.12 * P.a("eye_size"))
    corner = {"downturned": 5, "upturned": -5, "almond": -1.5}.get(eye_shape, 0)

    nose = P.t("nose_shape") or NEUTRAL["nose_shape"]
    nose_len = 0.2 * L * (1 + 0.15 * P.a("nose_length")) + {"button": -12, "pointed": 6, "hooked": 6, "flat": -6}.get(nose, 0)
    nb = eye_y + nose_len
    nw = {"straight": 18, "narrow": 14.5, "wide": 24, "broad": 27, "hooked": 18, "button": 16.5,
          "crooked": 18, "pointed": 15, "flat": 26}[nose] + 5 * P.a("nose_width")

    mouth = P.t("mouth_shape", default_note=False)
    if mouth is None:
        P.notes.append({"trait": "mouth_shape", "kind": "default",
                        "message": "Mouth / lips: not described. Drawn with neutral proportions."})
    my = nb + 0.085 * L + 8 * P.a("mouth_height") + 4
    mw = {"thin": 30, "full": 31, "wide": 38, "small": 24, "downturned": 31}.get(mouth, 30) + 7 * P.a("mouth_width")
    uh = {"thin": 3.5, "full": 8}.get(mouth, 5.5) + 3 * P.a("lip_fullness")
    lh = {"thin": 5, "full": 11}.get(mouth, 8) + 3 * P.a("lip_fullness")
    uh, lh = max(2.0, uh), max(3.0, lh)
    mouth_corner = 4 if mouth == "downturned" else 0

    brow_y = eye_y - 27 - 7 * P.a("eyebrow_height")
    jaw_y = top + 0.80 * L
    cheek_y = eye_y + 0.05 * L

    # --- face outline -----------------------------------------------------
    right = [
        (CX + 0.55 * T, top + 10),
        (CX + T, top + 0.20 * L),
        (CX + Wc, cheek_y),
    ]
    if jawline == "angular" or face == "square":
        right += [(CX + J + 4, jaw_y - 8), (CX + J - 6, jaw_y + 16)]
    else:
        right += [(CX + J, jaw_y)]
    if chin in ("square", "cleft"):
        right += [(CX + C, chin_y - 10), (CX + C * 0.55, chin_y - 1)]
    else:
        right += [(CX + C, chin_y - 9)]
    outline = [(CX, top)] + right + [(CX, chin_y)] + list(reversed(mirror(right)))
    face_segs = catmull_rom(outline, closed=True)
    face_pts = sample_segments(face_segs)

    def half_width_at(y: float) -> float:
        xs = [x for x, yy in face_pts if abs(yy - y) < 4 and x > CX]
        return (max(xs) - CX) if xs else Wc

    hair_len = P.t("hair_length", default_note=False)
    hair_color = P.t("hair_color", default_note=False)
    hair_style = P.t("hair_style", default_note=False)
    hairline = P.t("hairline", default_note=False)
    hair_described = any(v is not None for v in (hair_len, hair_color, hair_style, hairline))
    tone = HAIR_TONES.get(hair_color or "", DEFAULT_HAIR_TONE)
    if hair_described and hair_color is None and hair_len not in ("bald",):
        P.notes.append({"trait": "hair_color", "kind": "default",
                        "message": "Hair colour: not described. Drawn with a neutral mid-grey tone."})
    if hair_color:
        P.notes.append({"trait": "hair_color", "kind": "tone",
                        "message": f"Hair colour ({option_label('hair_color', hair_color)}) is drawn as a monochrome tone."})
    brow_tone = tone if hair_color not in ("white", "gray", "blonde", "light") else "#7a766f"

    # --- shoulders & neck -------------------------------------------------
    neck_w = max(42.0, 0.62 * J)
    neck_top = jaw_y + 10
    s.poly([(CX - 300, H), (CX - 290, H - 90), (CX - 170, H - 150), (CX - neck_w - 18, chin_y + 70),
            (CX + neck_w + 18, chin_y + 70), (CX + 170, H - 150), (CX + 290, H - 90), (CX + 300, H)],
           fill=SHIRT)
    shoulders = [(CX - 300, H - 70), (CX - 250, H - 120), (CX - 150, H - 150), (CX - neck_w - 10, chin_y + 62)]
    s.smooth(shoulders, stroke=INK, width=2.2)
    s.smooth(mirror(shoulders), stroke=INK, width=2.2)

    # long hair: back layer
    if hair_len == "long":
        back = [(CX - Wc - 30, cheek_y - 40), (CX - Wc - 40, chin_y - 10), (CX - Wc - 22, chin_y + 90),
                (CX - neck_w - 30, chin_y + 115), (CX, chin_y + 60)]
        back_full = back + list(reversed(mirror(back)))[1:]
        if hair_style == "curly":
            back_full = [(x + rng.uniform(-6, 6), y + rng.uniform(-6, 6)) for x, y in back_full]
        s.smooth(back_full, closed=True, fill=tone, stroke=INK, width=1.6)

    neck = [(CX - neck_w, neck_top), (CX - neck_w - 2, chin_y + 50), (CX - neck_w - 14, chin_y + 70),
            (CX + neck_w + 14, chin_y + 70), (CX + neck_w + 2, chin_y + 50), (CX + neck_w, neck_top)]
    s.poly(neck, fill=SKIN)
    s.smooth([(CX - neck_w, neck_top), (CX - neck_w - 2, chin_y + 48), (CX - neck_w - 14, chin_y + 70)], stroke=INK, width=2)
    s.smooth(mirror([(CX - neck_w, neck_top), (CX - neck_w - 2, chin_y + 48), (CX - neck_w - 14, chin_y + 70)]), stroke=INK, width=2)
    s.smooth([(CX - neck_w - 14, chin_y + 70), (CX, chin_y + 98), (CX + neck_w + 14, chin_y + 70)], stroke=SOFT, width=1.4)
    s.smooth([(CX - 30, chin_y + 18), (CX, chin_y + 26), (CX + 30, chin_y + 18)], stroke=SOFT, width=6, alpha=0.08)

    # --- ears -------------------------------------------------------------
    ears = P.t("ears") or NEUTRAL["ears"]
    ear_scale = {"small": 0.85, "average": 1.0, "large": 1.15, "protruding": 1.08}[ears] * (1 + 0.15 * P.a("ear_size"))
    ear_out = {"protruding": 1.55}.get(ears, 1.0)
    ey0 = brow_y + 8
    ehgt = (nb - brow_y + 6) * ear_scale
    ewid = 19 * ear_scale * ear_out
    for side in (1, -1):
        bx = CX + side * (half_width_at(ey0 + ehgt * 0.4) - 6)
        ear = [(bx, ey0 + 4), (bx + side * ewid * 0.7, ey0 - 4), (bx + side * ewid, ey0 + ehgt * 0.22),
               (bx + side * ewid * 0.9, ey0 + ehgt * 0.58), (bx + side * ewid * 0.42, ey0 + ehgt),
               (bx - side * 2, ey0 + ehgt * 0.86)]
        s.smooth(ear, closed=True, fill=SKIN, stroke=INK, width=2)
        inner = [(bx + side * ewid * 0.25, ey0 + ehgt * 0.12), (bx + side * ewid * 0.62, ey0 + ehgt * 0.22),
                 (bx + side * ewid * 0.58, ey0 + ehgt * 0.58), (bx + side * ewid * 0.3, ey0 + ehgt * 0.72)]
        s.smooth(inner, stroke=SOFT, width=1.4)
    ear_lobe = {1: (CX + half_width_at(ey0 + ehgt * 0.4) - 6 + ewid * 0.42, ey0 + ehgt - 6),
                -1: (CX - half_width_at(ey0 + ehgt * 0.4) + 6 - ewid * 0.42, ey0 + ehgt - 6)}

    # --- face -------------------------------------------------------------
    s.bezier(face_segs, closed=True, fill=SKIN)
    # soft cheekbone / jaw shading
    for side in (1, -1):
        shade = [(CX + side * (Wc - 10), cheek_y + 6), (CX + side * (J - 2), jaw_y), (CX + side * (C + 10), chin_y - 18)]
        s.smooth(shade, stroke=SOFT, width=16, alpha=0.06)
    s.bezier(face_segs, closed=True, stroke=INK, width=2.4)

    if chin == "cleft":
        s.smooth([(CX, chin_y - 18), (CX + 1, chin_y - 10), (CX, chin_y - 3)], stroke=SOFT, width=1.6)

    # --- age lines --------------------------------------------------------
    hair_y_center = top + 0.16 * L
    if age in ("senior", "middle_aged"):
        strength = 1.0 if age == "senior" else 0.55
        for side in (1, -1):
            fold = [(CX + side * (nw + 6), nb - 6), (CX + side * (nw + 14), nb + 16), (CX + side * (mw + 8), my + 6)]
            s.smooth(fold, stroke=SOFT, width=1.5, alpha=0.75 * strength)
        lines = 3 if age == "senior" else 2
        for i in range(lines):
            yy = brow_y - 22 - i * 11
            if yy > hair_y_center + 12:
                s.smooth([(CX - 46 + i * 6, yy + 2), (CX, yy - 2), (CX + 46 - i * 6, yy + 2)], stroke=SOFT, width=1.1, alpha=0.6 * strength)
        if age == "senior":
            for side in (1, -1):
                ox = CX + side * (S + ew + 4)
                for i, dy in enumerate((-6, 0, 6)):
                    s.line((ox, eye_y + dy), (ox + side * 10, eye_y + dy + (i - 1) * 4), stroke=SOFT, width=1, alpha=0.6)
                s.smooth([(CX + side * (S - ew * 0.7), eye_y + eh + 6), (CX + side * S, eye_y + eh + 10),
                          (CX + side * (S + ew * 0.6), eye_y + eh + 5)], stroke=SOFT, width=1, alpha=0.55)

    # --- facial hair (under mouth/nose) ------------------------------------
    facial = P.t("facial_hair", default_note=False)
    if facial is None:
        P.notes.append({"trait": "facial_hair", "kind": "default",
                        "message": "Facial hair: not described. None is drawn; this is not a statement that there was none."})
    beard_tone = tone if hair_color not in ("white", "light", "blonde", "gray") else "#8a857d"

    def mustache():
        top_y = nb + 9
        shape = [(CX - mw - 6, my + 3), (CX - mw * 0.75, top_y + 4), (CX - 6, top_y), (CX, top_y + 2),
                 (CX + 6, top_y), (CX + mw * 0.75, top_y + 4), (CX + mw + 6, my + 3),
                 (CX + mw * 0.5, my - uh - 2), (CX, my - uh - 1), (CX - mw * 0.5, my - uh - 2)]
        s.smooth(shape, closed=True, fill=beard_tone, alpha=0.95)
        for i in range(14):
            x = CX - mw + (2 * mw) * (i / 13)
            s.line((x, top_y + 6), (x + (x - CX) * 0.12, my - uh), stroke="#000000", width=0.8, alpha=0.25)

    def chin_patch():
        cw = min(C, 26) + 6
        patch = [(CX - mw * 0.55, my + lh + 3), (CX - cw, chin_y - 16), (CX - cw * 0.55, chin_y + 1),
                 (CX, chin_y + 5), (CX + cw * 0.55, chin_y + 1), (CX + cw, chin_y - 16), (CX + mw * 0.55, my + lh + 3),
                 (CX, my + lh + 6)]
        s.smooth(patch, closed=True, fill=beard_tone, alpha=0.85)

    if facial == "stubble":
        region = [p for p in face_pts if p[1] > my - 30]
        region.sort(key=lambda p: math.atan2(p[1] - (my - 30), p[0] - CX))
        poly = region
        count = 0
        while count < 900:
            x = rng.uniform(CX - Wc, CX + Wc)
            y = rng.uniform(nb + 6, chin_y + 4)
            in_lip_band = abs(x - CX) < mw + 8 and nb + 8 < y < my - uh - 2
            in_mouth = ((x - CX) / (mw + 5)) ** 2 + ((y - my - 1) / (lh + 5)) ** 2 < 1
            if (point_in_poly(x, y, poly) or in_lip_band) and not in_mouth and point_in_poly(x, y, face_pts):
                s.ellipse(x, y, 0.9, 0.9, fill=beard_tone, alpha=rng.uniform(0.35, 0.65))
                count += 1
            else:
                count += 0.05
    elif facial == "mustache":
        mustache()
    elif facial == "goatee":
        chin_patch()
        mustache()
    elif facial == "full_beard":
        lower = [p for p in face_pts if p[1] > nb - 8]
        lower.sort(key=lambda p: math.atan2(p[1] - (nb - 8), p[0] - CX))
        expanded = [(CX + (x - CX) * 1.04, y + (6 if y > chin_y - 30 else 2)) for x, y in lower]
        inner = [(CX + Wc * 0.74, nb - 8), (CX + mw + 12, my - 6), (CX + mw * 0.5, nb + 12), (CX, nb + 10),
                 (CX - mw * 0.5, nb + 12), (CX - mw - 12, my - 6), (CX - Wc * 0.74, nb - 8)]
        beard_poly = expanded + list(reversed(inner))
        s.poly(beard_poly, closed=True, fill=beard_tone, alpha=0.92)
        for _ in range(140):
            x = rng.uniform(CX - Wc, CX + Wc)
            y = rng.uniform(nb, chin_y + 8)
            if point_in_poly(x, y, beard_poly):
                ang = math.atan2(y - eye_y, x - CX) + rng.uniform(-0.3, 0.3)
                s.line((x, y), (x + math.cos(ang) * 7, y + math.sin(ang) * 7), stroke="#000000", width=0.9, alpha=0.28)

    # --- mouth -------------------------------------------------------------
    lc, rc = (CX - mw, my + mouth_corner), (CX + mw, my + mouth_corner)
    upper = [lc, (CX - mw * 0.55, my - uh * 0.75), (CX - 8, my - uh), (CX, my - uh + 2.4), (CX + 8, my - uh),
             (CX + mw * 0.55, my - uh * 0.75), rc, (CX + mw * 0.4, my + 1), (CX, my + 1.6), (CX - mw * 0.4, my + 1)]
    lower = [lc, (CX - mw * 0.4, my + 1.5), (CX, my + 2), (CX + mw * 0.4, my + 1.5), rc,
             (CX + mw * 0.55, my + lh * 0.75), (CX, my + lh), (CX - mw * 0.55, my + lh * 0.75)]
    s.smooth(lower, closed=True, fill="#ece8e1", stroke=SOFT, width=1.1)
    s.smooth(upper, closed=True, fill="#e3dfd7", stroke=SOFT, width=1.2)
    s.smooth([lc, (CX - mw * 0.4, my + 1), (CX, my + 2), (CX + mw * 0.4, my + 1), rc], stroke=INK, width=2.2)
    s.smooth([(CX - 12, my + lh + 6), (CX, my + lh + 8), (CX + 12, my + lh + 6)], stroke=SOFT, width=4, alpha=0.14)
    if facial not in ("mustache", "goatee", "full_beard"):
        s.line((CX - 5, nb + 9), (CX - 7, my - uh), stroke=SOFT, width=1, alpha=0.35)
        s.line((CX + 5, nb + 9), (CX + 7, my - uh), stroke=SOFT, width=1, alpha=0.35)

    # --- nose --------------------------------------------------------------
    bend = 6 if nose == "crooked" else 0
    for side in (-1, 1):
        start = (CX + side * 9, eye_y + 4)
        mid_x = CX + side * nw * 0.45 + (bend if side == 1 else bend * 0.6)
        bump = -6 if (nose == "hooked" and side == -1) else 0
        end = (CX + side * nw * 0.72 + bend * 0.4, nb - 14)
        s.smooth([start, (mid_x + bump, (eye_y + nb) / 2), end], stroke=SOFT, width=1.4, alpha=0.75 if side == -1 else 0.4)
    s.smooth([(CX - nw * 0.9, nb - 26), (CX - nw * 1.05, nb - 6), (CX - nw * 0.6, nb + 6)], stroke=SOFT, width=10, alpha=0.06)
    tip_drop = {"pointed": 5, "hooked": 6, "button": -1, "flat": -2}.get(nose, 2)
    for side in (-1, 1):
        wing = [(CX + side * nw * 0.55, nb - 11), (CX + side * nw * 1.0, nb - 5), (CX + side * nw * 0.95, nb + 3),
                (CX + side * nw * 0.62, nb + 5)]
        s.smooth(wing, stroke=INK, width=1.9)
    tip = [(CX - nw * 0.5, nb + 3), (CX - nw * 0.2, nb + 5 + tip_drop * 0.6), (CX + bend * 0.3, nb + 6 + tip_drop),
           (CX + nw * 0.2, nb + 5 + tip_drop * 0.6), (CX + nw * 0.5, nb + 3)]
    s.smooth(tip, stroke=INK, width=1.7)
    if nose == "button":
        s.smooth([(CX - nw * 0.35, nb - 4), (CX, nb - 9), (CX + nw * 0.35, nb - 4)], stroke=SOFT, width=1.1, alpha=0.6)
    for side in (-1, 1):
        s.ellipse(CX + side * nw * 0.45 + bend * 0.3, nb + 1.5, 4.2 if nose not in ("narrow", "pointed") else 3.2, 2.3,
                  fill="#2d2d2d", alpha=0.85)

    # --- eyes --------------------------------------------------------------
    for side in (-1, 1):
        ex = CX + side * S
        inner_c = (ex - side * ew, eye_y)
        outer_c = (ex + side * ew, eye_y + corner)
        up_seg = (inner_c, (inner_c[0] + side * ew * 0.55, eye_y - eh * 1.55),
                  (outer_c[0] - side * ew * 0.6, outer_c[1] - eh * 1.4), outer_c)
        lo_seg = (outer_c, (outer_c[0] - side * ew * 0.55, outer_c[1] + eh * 0.95),
                  (inner_c[0] + side * ew * 0.5, eye_y + eh * 0.9), inner_c)
        eye_poly = sample_segments([up_seg, lo_seg])
        if eye_shape == "deep_set":
            s.smooth([(ex - side * ew, eye_y - eh - 2), (ex, eye_y - eh * 2 - 4), (ex + side * ew * 1.1, eye_y - eh)],
                     stroke=SOFT, width=9, alpha=0.12)
        s.bezier([up_seg, lo_seg], closed=True, fill="#ffffff")
        clip = s.clip_group(eye_poly)
        ir = min(eh * 0.95 + 2.5, 10.0) if eye_shape != "narrow" else 8.0
        icy = eye_y - eh * 0.05 + corner * 0.4
        clip.ellipse(ex + side * 1, icy, ir, ir, fill="#7a7a7a", stroke="#3a3a3a", width=1.2)
        clip.ellipse(ex + side * 1, icy, ir * 0.45, ir * 0.45, fill="#141414")
        clip.ellipse(ex + side * 1 - 2.6, icy - 2.6, 1.6, 1.6, fill="#ffffff")
        clip.smooth([inner_c, (ex, eye_y - eh * 1.2), outer_c], stroke=SOFT, width=4, alpha=0.18)
        s.bezier([up_seg], stroke=INK, width=2.6)
        s.bezier([lo_seg], stroke=SOFT, width=1.3)
        crease_off = 2.5 if eye_shape == "hooded" else eh * 0.9 + 3
        crease = [(inner_c[0] + side * 4, eye_y - eh * 0.5 - crease_off * 0.5),
                  (ex, eye_y - eh * 1.15 - crease_off), (outer_c[0] - side * 2, outer_c[1] - eh * 0.7 - crease_off * 0.4)]
        s.smooth(crease, stroke=SOFT if eye_shape != "hooded" else INK, width=1.3 if eye_shape != "hooded" else 1.8,
                 alpha=0.7)

    # --- eyebrows ------------------------------------------------------------
    thick_key = P.t("eyebrow_thickness") or NEUTRAL["eyebrow_thickness"]
    shape_key = P.t("eyebrow_shape") or NEUTRAL["eyebrow_shape"]
    bt = {"thin": 3.2, "medium": 5.5, "thick": 8.5, "bushy": 11}[thick_key] + 3 * P.a("eyebrow_thickness")
    bt = max(1.8, bt)
    offsets = {"straight": [0, -1, -2, -2, 0], "arched": [2, -3, -8, -6, 2], "angled": [2, -4, -10, -3, 4],
               "curved": [3, -3, -6, -4, 3], "unibrow": [0, -1, -2, -2, 0]}[shape_key]
    profile_t = [1.0, 1.0, 0.86, 0.62, 0.32]
    for side in (-1, 1):
        ex = CX + side * S
        xs = [ex - side * ew * 0.95, ex - side * ew * 0.4, ex + side * ew * 0.25, ex + side * ew * 0.8, ex + side * ew * 1.28]
        centre = [(x, brow_y + o + (i * 1.2 if eye_shape == "downturned" else 0)) for i, (x, o) in enumerate(zip(xs, offsets))]
        top_edge = [(x, y - bt * w / 2) for (x, y), w in zip(centre, profile_t)]
        bot_edge = [(x, y + bt * w / 2) for (x, y), w in zip(centre, profile_t)]
        s.smooth(top_edge + list(reversed(bot_edge)), closed=True, fill=brow_tone, alpha=0.95)
        if thick_key in ("thick", "bushy"):
            for i in range(int(10 + bt * 2)):
                tt = rng.random()
                x = xs[0] + (xs[-1] - xs[0]) * tt
                y = brow_y + rng.uniform(-bt / 2, bt / 2) + offsets[min(4, int(tt * 4.99))]
                s.line((x, y), (x + side * 5, y - 2.5), stroke="#000000", width=0.9, alpha=0.3)
    if shape_key == "unibrow":
        s.smooth([(CX - S + ew * 0.95, brow_y + 1), (CX, brow_y + 2), (CX + S - ew * 0.95, brow_y + 1)],
                 stroke=brow_tone, width=max(2.0, bt * 0.6), alpha=0.85)

    # --- hair ----------------------------------------------------------------
    _draw_hair(s, P, rng, top=top, L=L, T=T, Wc=Wc, eye_y=eye_y, cheek_y=cheek_y, tone=tone,
               hair_len=hair_len, hair_style=hair_style, hairline=hairline, hair_described=hair_described,
               half_width_at=half_width_at)

    # --- eyewear -------------------------------------------------------------
    eyewear = P.t("eyewear", default_note=False)
    if eyewear and eyewear != "none":
        for side in (-1, 1):
            ex = CX + side * S
            if eyewear == "round_glasses":
                s.ellipse(ex, eye_y - 1, ew + 7, ew + 4, stroke=INK, width=2.6)
            else:
                rw, rh, r = ew + 9, eh + 11, 8
                x0, x1, y0, y1 = ex - rw, ex + rw, eye_y - rh, eye_y + rh + 2
                pts = [(x0 + r, y0), (x1 - r, y0), (x1, y0 + r), (x1, y1 - r), (x1 - r, y1), (x0 + r, y1), (x0, y1 - r), (x0, y0 + r)]
                if eyewear == "sunglasses":
                    s.smooth(pts, closed=True, fill="#232323", stroke=INK, width=2.4, alpha=0.95)
                else:
                    s.smooth(pts, closed=True, stroke=INK, width=2.6 if eyewear == "rectangular_glasses" else 2.0)
            s.line((ex + side * (ew + 8), eye_y - 6), (CX + side * (half_width_at(eye_y) + 2), eye_y - 9), stroke=INK, width=2.2)
        s.smooth([(CX - S + ew + 6, eye_y - 4), (CX, eye_y - 9), (CX + S - ew - 6, eye_y - 4)], stroke=INK, width=2.2)
        if eyewear == "glasses":
            P.notes.append({"trait": "eyewear", "kind": "limitation",
                            "message": "Eyewear: glasses mentioned without a frame style. Drawn with a generic frame."})
        if eyewear == "sunglasses":
            P.notes.append({"trait": "eyewear", "kind": "limitation",
                            "message": "Sunglasses hide the eyes; eye details are covered in the composite."})

    # --- distinctive marks -----------------------------------------------------
    anchors = {
        "forehead": (CX + 18, (top + 0.16 * L + brow_y) / 2 + 4),
        "left_eyebrow": (CX + S + 4, brow_y - 2), "right_eyebrow": (CX - S - 4, brow_y - 2),
        "left_eye": (CX + S + ew + 8, eye_y + 2), "right_eye": (CX - S - ew - 8, eye_y + 2),
        "nose": (CX + 7, (eye_y + nb) / 2 + 12),
        "left_cheek": (CX + S + 14, eye_y + 0.115 * L), "right_cheek": (CX - S - 14, eye_y + 0.115 * L),
        "upper_lip": (CX + 16, my - uh - 6), "lower_lip": (CX + 10, my + lh + 1),
        "chin": (CX + 10, chin_y - 22),
        "left_jaw": (CX + J - 14, jaw_y - 4), "right_jaw": (CX - J + 14, jaw_y - 4),
        "left_ear": ear_lobe[1], "right_ear": ear_lobe[-1],
        "neck": (CX + 18, chin_y + 48),
    }
    for mark in profile.marks:
        _draw_mark(s, P, rng, mark, anchors, S=S, nb=nb, eye_y=eye_y)

    # --- recorded-only traits ------------------------------------------------------
    for key in ("eye_color", "skin_tone"):
        tv = profile.traits.get(key)
        if tv and tv.value:
            P.notes.append({"trait": key, "kind": "not_rendered",
                            "message": f"{TRAIT_BY_KEY[key]['label']} ({option_label(key, tv.value)}) is recorded in the profile but not drawn in a monochrome composite."})
    if profile.observations.strip():
        P.notes.append({"trait": "observations", "kind": "not_rendered",
                        "message": "Additional observations are recorded in the profile and report, not drawn."})

    # --- caption band --------------------------------------------------------------
    s.poly([(0, H - 30), (W, H - 30), (W, H), (0, H)], fill=PAPER)
    s.line((0, H - 30), (W, H - 30), stroke="#cfccc4", width=1)
    s.text(16, H - 11, "PROCEDURAL COMPOSITE · NOT A PHOTOGRAPH", size=11, fill="#5f5c56")
    if caption:
        s.text(W - 16, H - 11, caption[:40].upper(), size=11, fill="#5f5c56", anchor="end")

    svg = to_svg(s, "VeriSketch procedural composite")
    return RenderResult(svg=svg, scene=s, notes=_dedupe(P.notes), seed=seed)


def _dedupe(notes: list[dict]) -> list[dict]:
    seen, out = set(), []
    for n in notes:
        k = (n["trait"], n["message"])
        if k not in seen:
            seen.add(k)
            out.append(n)
    return out


def _draw_hair(s: Scene, P: _Params, rng: random.Random, *, top, L, T, Wc, eye_y, cheek_y, tone,
               hair_len, hair_style, hairline, hair_described, half_width_at):
    if hair_len == "bald":
        if hairline and hairline != "normal":
            P.notes.append({"trait": "hairline", "kind": "limitation",
                            "message": "Hairline is not visible because the subject is described as bald."})
        return

    unspecified = not hair_described
    if unspecified:
        P.notes.append({"trait": "hair_length", "kind": "unspecified",
                        "message": "Hair: not described. Shown as a dashed outline, not an invented hairstyle."})
        hair_len, hair_style, hairline = "short", "straight", "normal"
    else:
        if hair_len is None:
            P.notes.append({"trait": "hair_length", "kind": "default",
                            "message": "Hair length: not described. Drawn short as a neutral default."})
            hair_len = "short"
        if hair_style is None:
            if hair_len not in ("shaved",):
                P.notes.append({"trait": "hair_style", "kind": "default",
                                "message": "Hair style: not described. Drawn straight as a neutral default."})
            hair_style = "straight"
        if hairline is None:
            hairline = "normal"

    vol = {"shaved": 3, "short": 11, "medium": 16, "long": 17}[hair_len]
    vol += {"curly": 15, "wavy": 6, "slicked_back": -6, "spiky": 4}.get(hair_style, 0)
    vol += 8 * P.a("hair_volume")
    vol = max(2.0, vol)

    hc = top + {"normal": 0.16, "high": 0.225, "low": 0.11, "receding": 0.175, "widows_peak": 0.16}[hairline] * L
    sideburn_y = top + 0.30 * L
    anchor_x = T * 0.98
    # hairline path from left temple to right temple
    if hairline == "receding":
        right_hl = [(CX + 0.22 * T, hc - 2), (CX + 0.52 * T, top + 0.075 * L), (CX + 0.8 * T, top + 0.13 * L),
                    (CX + anchor_x, sideburn_y)]
    elif hairline == "widows_peak":
        right_hl = [(CX + 0.12 * T, hc - 0.03 * L), (CX + 0.5 * T, hc - 0.01 * L), (CX + 0.85 * T, hc + 0.04 * L),
                    (CX + anchor_x, sideburn_y)]
    else:
        right_hl = [(CX + 0.5 * T, hc + 0.012 * L), (CX + 0.85 * T, hc + 0.06 * L), (CX + anchor_x, sideburn_y)]
    centre_y = hc + (0.055 * L if hairline == "widows_peak" else 0)
    if hair_style == "side_part" and not unspecified:
        # fringe sweeps from the part across the forehead
        right_hl = [(x, y + 6 * (1 - abs(x - CX) / T)) for x, y in right_hl]
    hl = list(reversed(mirror(right_hl))) + [(CX, centre_y)] + right_hl

    if hair_len in ("medium", "long"):
        low_y = cheek_y + (0.05 * L if hair_len == "medium" else 0.12 * L)
        side_in_r = [(CX + half_width_at(low_y) - 3, low_y), (CX + half_width_at(cheek_y - 30) - 1, cheek_y - 30)]
        outer_r = [(CX + Wc + vol + 2, low_y + 6), (CX + Wc + vol, cheek_y - 50), (CX + T + vol, top + 0.12 * L),
                   (CX + 0.55 * T + vol * 0.5, top - vol * 0.7)]
    else:
        side_in_r = []
        outer_r = [(CX + anchor_x + 3, sideburn_y + 4), (CX + T + vol * 0.7, top + 0.13 * L),
                   (CX + 0.55 * T + vol * 0.45, top - vol * 0.6)]
    outer = mirror(outer_r) + [(CX, top - vol)] + list(reversed(outer_r))  # left bottom -> crown -> right bottom

    # outer boundary styling
    outer_pts = sample_segments(catmull_rom(outer))
    if hair_style == "curly" and not unspecified:
        bumped = []
        for i in range(0, len(outer_pts), 6):
            x, y = outer_pts[i]
            nx, ny = x - CX, y - (top + 0.25 * L)
            d = math.hypot(nx, ny) or 1
            r = 5 + 3 * math.sin(i * 1.7)
            bumped.append((x + nx / d * r, y + ny / d * r))
        outer_pts = sample_segments(catmull_rom(bumped))
    elif hair_style == "wavy" and not unspecified:
        outer_pts = [(x + 3 * math.sin(i / 7), y + 3 * math.cos(i / 9)) for i, (x, y) in enumerate(outer_pts)]
    elif hair_style == "spiky" and not unspecified:
        spiked = []
        for i, (x, y) in enumerate(outer_pts):
            if y < top + 0.1 * L and i % 8 == 4:
                nx, ny = x - CX, y - (top + 0.3 * L)
                d = math.hypot(nx, ny) or 1
                spiked.append((x + nx / d * 14, y + ny / d * 14))
            else:
                spiked.append((x, y))
        outer_pts = spiked

    hl_pts = sample_segments(catmull_rom(hl))
    right_inner_up = sample_segments(catmull_rom(side_in_r + [right_hl[-1]])) if side_in_r else []
    left_inner_down = list(reversed(mirror(right_inner_up)))
    cap = outer_pts + right_inner_up + list(reversed(hl_pts)) + left_inner_down

    if unspecified:
        s.poly(cap, closed=True, fill="#9a978f", alpha=0.10)
        s.poly(cap, closed=True, stroke="#6e6b64", width=1.6, dash=(6, 5))
        return

    alpha = 0.16 if hair_len == "shaved" else 1.0
    s.poly(cap, closed=True, fill=tone, alpha=alpha)
    if hair_len == "shaved":
        for _ in range(500):
            x = rng.uniform(CX - T - vol, CX + T + vol)
            y = rng.uniform(top - vol, sideburn_y)
            if point_in_poly(x, y, cap):
                s.ellipse(x, y, 0.8, 0.8, fill=tone, alpha=0.6)
        s.poly(cap, closed=True, stroke=SOFT, width=1.2, alpha=0.6)
        return
    s.poly(cap, closed=True, stroke=INK, width=1.8)

    # strand texture in a lighter tone
    light = "#ffffff" if tone in ("#1b1b1b", "#2a2a2a", "#46423e", "#56504b", DEFAULT_HAIR_TONE) else "#2a2a2a"
    crown = (CX + (-0.3 * T if hair_style == "side_part" else 0), top - vol * 0.3)
    strands = 26 if hair_len != "short" else 18
    for i in range(strands):
        tpos = (i + 0.5) / strands
        idx = int(tpos * (len(hl_pts) - 1))
        hx, hy = hl_pts[idx]
        if hair_style == "slicked_back":
            pts = [(hx, hy - 2), ((hx + crown[0]) / 2 + (hx - CX) * 0.15, (hy + crown[1]) / 2), (crown[0] + (hx - CX) * 0.3, crown[1] + 6)]
        elif hair_style == "side_part":
            px = crown[0]
            pts = [(px + (hx - px) * 0.15, top + 0.02 * L), ((px + hx) / 2, (top + hy) / 2 - 4), (hx, hy - 3)]
        else:
            pts = [(crown[0] + (hx - CX) * 0.25, crown[1] + 8), ((crown[0] + hx) / 2 + (hx - CX) * 0.1, (crown[1] + hy) / 2),
                   (hx, hy - 3)]
            if hair_style == "wavy":
                pts.insert(2, (pts[1][0] + 4, (pts[1][1] + hy) / 2))
        s.smooth(pts, stroke=light, width=0.9, alpha=0.22)
    if hair_style == "curly":
        for _ in range(70):
            x = rng.uniform(CX - T - vol, CX + T + vol)
            y = rng.uniform(top - vol, sideburn_y + (0.2 * L if hair_len != "short" else 0))
            if point_in_poly(x, y, cap):
                r = rng.uniform(3, 5.5)
                a0 = rng.uniform(0, math.tau)
                arc = [(x + math.cos(a0 + t) * r, y + math.sin(a0 + t) * r) for t in (0, 1.2, 2.4, 3.4)]
                s.smooth(arc, stroke=light, width=0.9, alpha=0.3)
    if hair_style == "side_part":
        s.smooth([(crown[0], top - vol * 0.1), (crown[0] + 4, (top + hc) / 2), (crown[0] + 10, hc - 4)], stroke=light, width=1.4, alpha=0.4)


def _draw_mark(s: Scene, P: _Params, rng: random.Random, mark: Mark, anchors: dict, *, S, nb, eye_y):
    base = anchors.get(mark.location)
    if base is None:
        return
    x, y = base[0] + mark.dx * 30, base[1] + mark.dy * 30
    scale = {"small": 1.0, "medium": 1.45, "large": 2.1}[mark.size]
    loc_label = mark.location.replace("_", " ")
    if not mark.side_specified and mark.location.startswith(("left_", "right_")):
        P.notes.append({"trait": f"mark:{mark.id}", "kind": "limitation",
                        "message": f"{mark.type.capitalize()}: side not stated. Drawn on the subject's left; move it if the side becomes known."})
    if mark.type == "scar":
        length = 20 * scale
        ang = math.radians(-28)
        dx, dy = math.cos(ang) * length / 2, math.sin(ang) * length / 2
        s.smooth([(x - dx, y - dy), (x + dx * 0.1, y + dy * 0.1 + 1.5), (x + dx, y + dy)], stroke="#3b3b3b", width=2.1)
        ticks = 3 if scale < 1.3 else 5
        for i in range(ticks):
            t = (i + 1) / (ticks + 1) * 2 - 1
            px, py = x + dx * t, y + dy * t
            nx, ny = -math.sin(ang) * 4, math.cos(ang) * 4
            s.line((px - nx, py - ny), (px + nx, py + ny), stroke="#3b3b3b", width=1.1, alpha=0.8)
    elif mark.type == "mole":
        r = 3.0 * (1 + (scale - 1) * 0.6)
        s.ellipse(x, y, r, r, fill="#2a2a2a")
    elif mark.type == "birthmark":
        pts = []
        for i in range(8):
            a = i / 8 * math.tau
            r = 9 * scale * rng.uniform(0.65, 1.1)
            pts.append((x + math.cos(a) * r * 1.3, y + math.sin(a) * r))
        s.smooth(pts, closed=True, fill="#8c8880", alpha=0.32)
    elif mark.type == "tattoo":
        w, h = 11 * scale, 8 * scale
        box = [(x - w, y - h), (x + w, y - h), (x + w, y + h), (x - w, y + h)]
        clip = s.clip_group(box)
        for i in range(-6, 7):
            clip.line((x + i * 4 - h, y - h), (x + i * 4 + h, y + h), stroke="#3a3a3a", width=1, alpha=0.7)
        s.poly(box, closed=True, stroke="#3a3a3a", width=1.2)
        P.notes.append({"trait": f"mark:{mark.id}", "kind": "limitation",
                        "message": f"Tattoo ({loc_label}): design not specified. Drawn as a generic hatched mark."})
    elif mark.type == "piercing":
        s.ellipse(x, y + 3, 3.4, 3.4, stroke="#2a2a2a", width=1.5)
    elif mark.type == "freckles":
        for _ in range(26):
            side = rng.choice((-1, 1))
            fx = CX + side * rng.uniform(8, S + 10)
            fy = rng.uniform(eye_y + 18, nb + 6)
            s.ellipse(fx, fy, 1.3, 1.3, fill="#6b665e", alpha=0.6)
