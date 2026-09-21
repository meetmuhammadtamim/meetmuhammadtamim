"""Generate Bauhaus SVG assets for the GitHub profile README.

Run:  pip install fonttools brotli uharfbuzz
      python tools/build_assets.py

All lettering is converted to vector paths (Outfit, shaped with HarfBuzz), so the
images need no font and render the same everywhere GitHub shows them.
Every asset has a light and a dark variant for GitHub's two themes.
"""
import io, os, math
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
import uharfbuzz as hb

HERE = os.path.dirname(os.path.abspath(__file__))
# Outfit ships with the portfolio site; set OUTFIT_WOFF2 if it lives elsewhere.
FONT_SRC = os.environ.get("OUTFIT_WOFF2", os.path.join(HERE, "..", "..", "portfolio", "public", "fonts", "outfit-latin.woff2"))
OUT = os.path.join(HERE, "..")
ASSETS = os.path.join(OUT, "assets")
os.makedirs(ASSETS, exist_ok=True)

# Site palette (tokens.css, converted from oklch).
PAPER, INK, INK2, MUTED = "#f9f4ea", "#101822", "#2f3945", "#4c5663"
ACCENT, RED, YELLOW = "#1f6dd8", "#d02d27", "#ecbf00"
CARD_BLUE, CARD_YELLOW = "#3871e0", "#eeae3c"

THEMES = {
    # Colours for anything drawn straight onto GitHub's page background.
    "light": {"text": INK, "muted": MUTED, "edge": INK},
    "dark":  {"text": PAPER, "muted": "#c9c2b4", "edge": PAPER},
}

# ------------------------------------------------------------------ text to paths
class Face:
    def __init__(self, weight):
        f = TTFont(FONT_SRC)
        instancer.instantiateVariableFont(f, {"wght": weight}, inplace=True)
        f.flavor = None                  # save as plain TrueType; HarfBuzz cannot read WOFF2
        buf = io.BytesIO(); f.save(buf)
        self.tt = TTFont(io.BytesIO(buf.getvalue()))
        self.upem = self.tt["head"].unitsPerEm
        self.gs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.hb = hb.Font(hb.Face(hb.Blob(buf.getvalue())))

    def _shape(self, text):
        b = hb.Buffer(); b.add_str(text); b.guess_segment_properties()
        hb.shape(self.hb, b, {"kern": True, "liga": True})
        return b.glyph_infos, b.glyph_positions

    def width(self, text, size, tracking=0.0):
        infos, pos = self._shape(text)
        adv = sum(p.x_advance for p in pos) + tracking * self.upem * max(0, len(pos) - 1)
        return adv * size / self.upem

    def path(self, text, x, baseline, size, tracking=0.0):
        s = size / self.upem
        infos, pos = self._shape(text)
        pen = SVGPathPen(self.gs)
        cx = 0.0
        for i, (inf, p) in enumerate(zip(infos, pos)):
            name = self.order[inf.codepoint]
            tp = TransformPen(pen, (s, 0, 0, -s, x + (cx + p.x_offset) * s, baseline - p.y_offset * s))
            self.gs[name].draw(tp)
            cx += p.x_advance + (tracking * self.upem if i < len(pos) - 1 else 0)
        return pen.getCommands()

BLACK, BOLD, MED = Face(900), Face(700), Face(500)

def text(face, s, x, y, size, fill, tracking=0.0, anchor="start"):
    if anchor != "start":
        w = face.width(s, size, tracking)
        x = x - (w if anchor == "end" else w / 2)
    return f'<path fill="{fill}" d="{face.path(s, x, y, size, tracking)}"/>'

def wrap(face, s, size, max_w, tracking=0.0):
    lines, cur = [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if face.width(trial, size, tracking) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur); cur = word
    if cur: lines.append(cur)
    return lines

def arrow(x, y, size, color):
    """North-east arrow, drawn as strokes (Outfit has no arrow glyph)."""
    k = size
    return (f'<g stroke="{color}" stroke-width="{k*0.13:.1f}" stroke-linecap="square" fill="none">'
            f'<path d="M{x:.1f} {y:.1f} L{x+k:.1f} {y-k:.1f}"/>'
            f'<path d="M{x+k*0.35:.1f} {y-k:.1f} L{x+k:.1f} {y-k:.1f} L{x+k:.1f} {y-k*0.35:.1f}"/></g>')

def svg(w, h, body, title, display_w=None):
    dw = display_w or w
    dh = round(h * dw / w)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{dw}" height="{dh}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{title}"><title>{title}</title>{body}</svg>\n')

def save(name, content):
    with open(os.path.join(ASSETS, name), "w", encoding="utf-8") as fh:
        fh.write(content)

def logo_marks(x, cy, u):
    """The site's three-shape mark: red circle, blue square, yellow triangle."""
    return (f'<circle cx="{x+u/2}" cy="{cy}" r="{u/2}" fill="{RED}" stroke="{INK}" stroke-width="2"/>'
            f'<rect x="{x+u*1.35}" y="{cy-u/2}" width="{u}" height="{u}" fill="{ACCENT}" stroke="{INK}" stroke-width="2"/>'
            f'<path d="M{x+u*2.7+u/2} {cy-u/2} L{x+u*3.7} {cy+u/2} L{x+u*2.7} {cy+u/2} Z" fill="{YELLOW}" stroke="{INK}" stroke-width="2"/>')

# ------------------------------------------------------------------ banner
def banner(theme):
    t = THEMES[theme]
    W, H = 1600, 720
    bw, sh = 8, 18                       # border, hard shadow offset
    cx0, cy0, cw, ch = 24, 24, W - 24 * 2 - sh, H - 24 * 2 - sh
    split = cx0 + int(cw * 0.58)
    b = []
    b.append(f'<rect x="{cx0+sh}" y="{cy0+sh}" width="{cw}" height="{ch}" fill="{t["edge"]}"/>')
    b.append(f'<rect x="{cx0}" y="{cy0}" width="{cw}" height="{ch}" fill="{PAPER}"/>')

    # Right panel: blue stage, dot grid, circle, rotated square, square with triangle.
    rx, ry, rw, rh = split, cy0, cx0 + cw - split, ch
    b.append('<defs><pattern id="dots" width="28" height="28" patternUnits="userSpaceOnUse">'
             f'<circle cx="14" cy="14" r="2.6" fill="{PAPER}" fill-opacity="0.28"/></pattern>'
             f'<clipPath id="stage"><rect x="{rx}" y="{ry}" width="{rw}" height="{rh}"/></clipPath></defs>')
    b.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" fill="{ACCENT}"/>')
    b.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" fill="url(#dots)"/>')
    g = [f'<g clip-path="url(#stage)">']
    g.append(f'<circle cx="{rx+rw-70}" cy="{ry+80}" r="190" fill="{YELLOW}" stroke="{INK}" stroke-width="{bw}"/>')
    sq = 250
    g.append(f'<rect x="{rx+60}" y="{ry+rh-190}" width="{sq}" height="{sq}" fill="{RED}" stroke="{INK}" stroke-width="{bw}" '
             f'transform="rotate(45 {rx+60+sq/2} {ry+rh-190+sq/2})"/>')
    g.append('</g>')
    b += g
    ps, px, py = 230, rx + rw / 2 - 115, ry + rh / 2 - 115
    b.append(f'<rect x="{px+14}" y="{py+14}" width="{ps}" height="{ps}" fill="{INK}"/>')
    b.append(f'<rect x="{px}" y="{py}" width="{ps}" height="{ps}" fill="{PAPER}" stroke="{INK}" stroke-width="{bw}"/>')
    tri = 86
    b.append(f'<path d="M{px+ps/2} {py+ps/2-tri*0.55} L{px+ps/2+tri*0.6} {py+ps/2+tri*0.45} L{px+ps/2-tri*0.6} {py+ps/2+tri*0.45} Z" fill="{INK}"/>')
    b.append(f'<line x1="{split}" y1="{cy0}" x2="{split}" y2="{cy0+ch}" stroke="{INK}" stroke-width="{bw}"/>')

    # Left panel: brand row, constructivist headline, red lead bar with platforms.
    lx = cx0 + 64
    b.append(logo_marks(lx, cy0 + 84, 26))
    b.append(text(BLACK, "MUHAMMAD TAMIM", lx + 112, cy0 + 96, 34, INK, -0.01))
    avail = split - lx - 56
    lines = [("I FIX CONVERSION", INK), ("TRACKING THAT", INK), ("QUIETLY", INK), ("DOES NOT WORK.", RED)]
    size = 84
    while max(BLACK.width(l, size, -0.05) for l, _ in lines) > avail:
        size -= 1
    base = cy0 + 210
    for i, (l, col) in enumerate(lines):
        b.append(text(BLACK, l, lx, base + i * size * 0.9, size, col, -0.05))
    ly = base + (len(lines) - 1) * size * 0.9 + 70
    b.append(f'<rect x="{lx}" y="{ly-30}" width="8" height="46" fill="{RED}"/>')
    b.append(text(BOLD, "GA4  \u00b7  GOOGLE TAG MANAGER  \u00b7  GOOGLE ADS  \u00b7  META", lx + 30, ly + 4, 23, INK2, 0.1))
    b.append(f'<rect x="{cx0}" y="{cy0}" width="{cw}" height="{ch}" fill="none" stroke="{INK}" stroke-width="{bw}"/>')
    save(f"banner-{theme}.svg", svg(W, H, "".join(b),
         "Muhammad Tamim. I fix conversion tracking that quietly does not work. GA4, Google Tag Manager, Google Ads, Meta."))

def banner_phone(theme):
    t = THEMES[theme]
    W, bw, sh = 800, 6, 14
    cx0 = cy0 = 16
    cw = W - cx0 * 2 - sh
    lx, inner = cx0 + 44, cw - 88
    b, y = [], cy0 + 70
    b.append(logo_marks(lx, y - 12, 30))
    b.append(text(BLACK, "MUHAMMAD TAMIM", lx + 130, y, 38, INK, -0.01))
    lines = [("I FIX", INK), ("CONVERSION", INK), ("TRACKING THAT", INK), ("QUIETLY", INK), ("DOES NOT WORK.", RED)]
    size = 110
    while max(BLACK.width(l, size, -0.05) for l, _ in lines) > inner:
        size -= 1
    y += 30
    for i, (l, col) in enumerate(lines):
        y += size * (0.9 if i else 0.95)
        b.append(text(BLACK, l, lx, y, size, col, -0.05))
    y += 50
    tag_lines = ["GA4  ·  GOOGLE TAG MANAGER", "GOOGLE ADS  ·  META"]
    b.append(f'<rect x="{lx}" y="{y-6}" width="8" height="{len(tag_lines)*44+2}" fill="{RED}"/>')
    for i, l in enumerate(tag_lines):
        b.append(text(BOLD, l, lx + 30, y + 26 + i * 44, 28, INK2, 0.1))
    y += len(tag_lines) * 44 + 44
    split = y
    stage_h = 320
    ch = split - cy0 + stage_h
    H = cy0 + ch + sh + 16
    rx, ry, rw, rh = cx0, split, cw, stage_h
    top = [f'<rect x="{cx0+sh}" y="{cy0+sh}" width="{cw}" height="{ch}" fill="{t["edge"]}"/>',
           f'<rect x="{cx0}" y="{cy0}" width="{cw}" height="{ch}" fill="{PAPER}"/>',
           '<defs><pattern id="dotsp" width="26" height="26" patternUnits="userSpaceOnUse">'
           f'<circle cx="13" cy="13" r="2.4" fill="{PAPER}" fill-opacity="0.28"/></pattern>'
           f'<clipPath id="stagep"><rect x="{rx}" y="{ry}" width="{rw}" height="{rh}"/></clipPath></defs>',
           f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" fill="{ACCENT}"/>',
           f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" fill="url(#dotsp)"/>',
           f'<g clip-path="url(#stagep)">'
           f'<circle cx="{rx+rw-60}" cy="{ry+40}" r="150" fill="{YELLOW}" stroke="{INK}" stroke-width="{bw}"/>'
           f'<rect x="{rx+40}" y="{ry+rh-120}" width="200" height="200" fill="{RED}" stroke="{INK}" stroke-width="{bw}" '
           f'transform="rotate(45 {rx+140} {ry+rh-20})"/></g>']
    ps = 170; px, py = rx + rw / 2 - ps / 2, ry + rh / 2 - ps / 2
    top += [f'<rect x="{px+12}" y="{py+12}" width="{ps}" height="{ps}" fill="{INK}"/>',
            f'<rect x="{px}" y="{py}" width="{ps}" height="{ps}" fill="{PAPER}" stroke="{INK}" stroke-width="{bw}"/>',
            f'<path d="M{px+ps/2} {py+ps/2-36} L{px+ps/2+42} {py+ps/2+32} L{px+ps/2-42} {py+ps/2+32} Z" fill="{INK}"/>',
            f'<line x1="{cx0}" y1="{split}" x2="{cx0+cw}" y2="{split}" stroke="{INK}" stroke-width="{bw}"/>']
    frame = f'<rect x="{cx0}" y="{cy0}" width="{cw}" height="{ch}" fill="none" stroke="{INK}" stroke-width="{bw}"/>'
    save(f"banner-phone-{theme}.svg", svg(W, H, "".join(top + b) + frame,
         "Muhammad Tamim. I fix conversion tracking that quietly does not work. GA4, Google Tag Manager, Google Ads, Meta."))

# ------------------------------------------------------------------ section header
def header(slug, kicker, title, theme, mark=ACCENT, phone=False):
    t = THEMES[theme]
    W, ks, ts, rule = (800, 30, 76, 6) if phone else (1600, 24, 76, 8)
    m = ks * 0.92
    b = [f'<rect x="0" y="22" width="{m}" height="{m}" fill="{mark}" stroke="{t["edge"]}" stroke-width="2"/>',
         text(BOLD, kicker.upper(), m + 18, 22 + m * 0.86, ks, t["muted"], 0.12)]
    y = 22 + m + 18
    for i, l in enumerate(wrap(BLACK, title.upper(), ts, W, -0.05)):
        y += ts * (0.9 if i else 0.95)
        b.append(text(BLACK, l, 0, y, ts, t["text"], -0.05))
    y += 30
    b.append(f'<rect x="0" y="{y}" width="{W}" height="{rule}" fill="{t["edge"]}"/>')
    H = y + rule + 36                       # space below the rule before the text that follows
    suffix = "-phone" if phone else ""
    save(f"head-{slug}{suffix}-{theme}.svg", svg(W, H, "".join(b), f"{kicker}: {title}"))

# ------------------------------------------------------------------ tool card
def tool_card(slug, theme, *, fill, fg, rule, mark, mark_shape, label, title, body, facts, alt):
    t = THEMES[theme]
    W, bw, sh, pad = 800, 8, 16, 52
    x0, y0, cw = 16, 16, W - 16 * 2 - sh
    inner = cw - pad * 2
    parts, y = [], y0 + pad + 26
    parts.append(text(BOLD, label.upper(), x0 + pad, y, 22, fg, 0.12))
    y += 34
    tl = wrap(BLACK, title.upper(), 58, inner - 30, -0.035)
    for i, l in enumerate(tl):
        y += 56 if i else 60
        parts.append(text(BLACK, l, x0 + pad, y, 58, fg, -0.035))
    y += 28
    for l in wrap(MED, body, 28, inner):
        y += 42
        parts.append(text(MED, l, x0 + pad, y, 28, fg))
    y += 44
    parts.append(f'<rect x="{x0+pad}" y="{y}" width="{inner}" height="4" fill="{rule}"/>')
    colw = inner / len(facts)
    for i, (num, lab) in enumerate(facts):
        fx = x0 + pad + i * colw + (20 if i else 0)
        if i:
            parts.append(f'<rect x="{x0+pad+i*colw}" y="{y}" width="4" height="150" fill="{rule}"/>')
        parts.append(text(BLACK, num, fx, y + 78, 64, fg, -0.03))
        for j, ll in enumerate(wrap(BOLD, lab.upper(), 18, colw - 30, 0.1)):
            parts.append(text(BOLD, ll, fx, y + 112 + j * 24, 18, fg, 0.1))
    y += 150
    parts.append(f'<rect x="{x0+pad}" y="{y}" width="{inner}" height="4" fill="{rule}"/>')
    y += 64
    cta = "VIEW REPOSITORY"
    parts.append(text(BOLD, cta, x0 + pad, y, 24, fg, 0.08))
    aw = BOLD.width(cta, 24, 0.08)
    parts.append(arrow(x0 + pad + aw + 16, y - 2, 18, fg))
    ch = y + pad - y0 - 10
    H = y0 + ch + sh + 16
    mx, my, ms = x0 + cw - pad + 12, y0 + 30, 26
    if mark_shape == "circle":
        m = f'<circle cx="{mx}" cy="{my+ms/2}" r="{ms/2}" fill="{mark}" stroke="{INK}" stroke-width="3"/>'
    elif mark_shape == "square":
        m = f'<rect x="{mx-ms/2}" y="{my}" width="{ms}" height="{ms}" fill="{mark}" stroke="{INK}" stroke-width="3"/>'
    else:
        m = f'<path d="M{mx} {my} L{mx+ms/2} {my+ms} L{mx-ms/2} {my+ms} Z" fill="{mark}"/>'
    b = [f'<rect x="{x0+sh}" y="{y0+sh}" width="{cw}" height="{ch}" fill="{t["edge"]}"/>',
         f'<rect x="{x0}" y="{y0}" width="{cw}" height="{ch}" fill="{fill}" stroke="{INK}" stroke-width="{bw}"/>',
         *parts, m]
    save(f"tool-{slug}-{theme}.svg", svg(W, H, "".join(b), alt, display_w=380))
    return H

# ------------------------------------------------------------------ link button
def button(slug, label, theme, fill=ACCENT, fg=PAPER):
    t = THEMES[theme]
    size, track, padx, h, bw, sh = 30, 0.06, 40, 84, 6, 10
    tw = BOLD.width(label.upper(), size, track)
    w = int(tw + padx * 2 + 34)
    W, H = w + sh + bw, h + sh + bw
    b = [f'<rect x="{bw/2+sh}" y="{bw/2+sh}" width="{w}" height="{h}" fill="{t["edge"]}"/>',
         f'<rect x="{bw/2}" y="{bw/2}" width="{w}" height="{h}" fill="{fill}" stroke="{INK}" stroke-width="{bw}"/>',
         text(BOLD, label.upper(), bw / 2 + padx, bw / 2 + h / 2 + size * 0.36, size, fg, track),
         arrow(bw / 2 + padx + tw + 14, bw / 2 + h / 2 + 11, 20, fg)]
    save(f"btn-{slug}-{theme}.svg", svg(W, H, "".join(b), label))

# ------------------------------------------------------------------ build
for th in THEMES:
    banner(th)
    banner_phone(th)
    for phone in (False, True):
        header("tools", "Selected work", "Tools and test evidence.", th, phone=phone)
        header("background", "Background", "How I work.", th, mark=RED, phone=phone)
    tool_card("ecommerce", th, fill=CARD_BLUE, fg="#ffffff", rule="#ffffff", mark=YELLOW, mark_shape="circle",
              label="Conversion tracking audit", title="Ecommerce tracking audit",
              body="Walks a real store from homepage to checkout and records which events reached GA4 and Meta, not just which ones fired on the page.",
              facts=[("4", "Stages checked"), ("3", "Meta events confirmed"), ("3", "GA4 requests missing")],
              alt="Ecommerce tracking audit: walks a store to checkout and records which events reached GA4 and Meta. 4 stages checked, 3 Meta events confirmed, 3 GA4 requests missing.")
    tool_card("sitemap", th, fill=CARD_YELLOW, fg=INK, rule=INK, mark=RED, mark_shape="triangle",
              label="Site audit", title="Sitemap website downloader",
              body="Pulls every page in a sitemap into one searchable local copy, for finding information that conflicts across a large site.",
              facts=[("145", "URLs found"), ("144", "Pages saved"), ("993", "Assets saved")],
              alt="Sitemap website downloader: pulls every sitemap page into one searchable local copy. 145 URLs found, 144 pages saved, 993 assets saved.")
    button("website", "muhammadtamim.com", th)
    button("linkedin", "LinkedIn", th, fill=YELLOW, fg=INK)
    button("facebook", "Facebook", th, fill=PAPER, fg=INK)

print("assets:", sorted(os.listdir(ASSETS)))
