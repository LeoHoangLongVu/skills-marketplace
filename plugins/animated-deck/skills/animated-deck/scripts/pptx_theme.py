#!/usr/bin/env python3
"""Extract a deck theme from a PowerPoint file (.pptx / .potx).

A PowerPoint file is a zip of OOXML. This pulls the brand colour scheme and fonts
from ppt/theme/theme1.xml, the slide size from ppt/presentation.xml, and lists
ppt/media/* so you can lift a logo. It then emits a ready `:root{}` block that
drops straight over the template's theme so the generated HTML deck matches the
brand. See references/pptx-template.md for how to wire the fonts, logo and a
light-vs-dark background.

Usage:
  python3 pptx_theme.py BRAND.potx                 # report + :root block to stdout
  python3 pptx_theme.py BRAND.pptx --light         # light-background variant
  python3 pptx_theme.py BRAND.pptx --out theme.css # also write the :root block
  python3 pptx_theme.py BRAND.pptx --logo logo.png # extract the largest image

Stdlib only (zipfile + xml.etree) — no python-pptx needed.
"""
import argparse, colorsys, os, sys, zipfile
import xml.etree.ElementTree as ET

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
EMU_PER_IN = 914400

# MS Office fonts -> a distinctive, web-available substitute (avoid generic defaults).
FONT_SUB = {
    "calibri": "Lato", "calibri light": "Lato", "arial": "Archivo", "helvetica": "Archivo",
    "segoe ui": "Open Sans", "cambria": "Lora", "georgia": "Lora",
    "times new roman": "Lora", "century gothic": "Questrial", "verdana": "Source Sans 3",
    "tahoma": "Source Sans 3", "trebuchet ms": "Mulish", "garamond": "EB Garamond",
    "franklin gothic": "Oswald", "corbel": "Hanken Grotesk",
}

def _hex(node):
    """Resolve a colour child (<a:srgbClr>/<a:sysClr>) to RRGGBB, or None."""
    if node is None:
        return None
    srgb = node.find(f"{A}srgbClr")
    if srgb is not None:
        return srgb.get("val", "").upper()
    sysc = node.find(f"{A}sysClr")
    if sysc is not None and sysc.get("lastClr"):
        return sysc.get("lastClr", "").upper()
    return None

def _rgb(h):
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _hexf(rgb):
    return "{:02X}{:02X}{:02X}".format(*(max(0, min(255, round(c))) for c in rgb))

def _lum(h):
    r, g, b = (c / 255 for c in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def _mix(h, target, t):
    """Linear-interpolate colour h toward target (a hex) by fraction t."""
    a, b = _rgb(h), _rgb(target)
    return _hexf(tuple(a[i] + (b[i] - a[i]) * t for i in range(3)))

def _hue(h):
    r, g, b = (c / 255 for c in _rgb(h))
    return colorsys.rgb_to_hls(r, g, b)[0] * 360

def _sat(h):
    r, g, b = (c / 255 for c in _rgb(h))
    return colorsys.rgb_to_hls(r, g, b)[2]

def read(zf, name):
    try:
        return zf.read(name)
    except KeyError:
        return None

def first(zf, prefix):
    for n in zf.namelist():
        if n.startswith(prefix) and n.lower().endswith(".xml"):
            return n
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    ap.add_argument("--light", action="store_true", help="emit a light-background variant")
    ap.add_argument("--out", help="write the :root block to this file")
    ap.add_argument("--logo", help="extract one ppt/media image to this path (see --logo-name)")
    ap.add_argument("--logo-name", help="which media file to extract (e.g. image3.png); "
                                        "default is the largest, which is OFTEN a background")
    ap.add_argument("--media-dir", help="extract ALL ppt/media images to this dir so you can "
                                        "inspect them and pick the real logo")
    args = ap.parse_args()

    if not os.path.exists(args.pptx):
        sys.exit(f"not found: {args.pptx}")

    with zipfile.ZipFile(args.pptx) as zf:
        names = zf.namelist()

        # ---- colours + fonts from the theme ----
        tname = first(zf, "ppt/theme/theme")
        if not tname:
            sys.exit("no ppt/theme/themeN.xml in this file — not a PowerPoint template?")
        theme = ET.fromstring(zf.read(tname))
        clr = theme.find(f"{A}themeElements/{A}clrScheme")
        scheme = {}
        for slot in ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3",
                     "accent4", "accent5", "accent6", "hlink", "folHlink"):
            scheme[slot] = _hex(clr.find(f"{A}{slot}")) if clr is not None else None
        fonts = theme.find(f"{A}themeElements/{A}fontScheme")
        def face(kind):
            el = fonts.find(f"{A}{kind}/{A}latin") if fonts is not None else None
            return el.get("typeface") if el is not None else None
        major, minor = face("majorFont"), face("minorFont")

        # ---- slide size ----
        pres_xml = read(zf, "ppt/presentation.xml")
        w_in = h_in = None
        if pres_xml:
            sld = ET.fromstring(pres_xml).find(f"{P}sldSz")
            if sld is not None:
                w_in = int(sld.get("cx")) / EMU_PER_IN
                h_in = int(sld.get("cy")) / EMU_PER_IN

        # ---- media (logos / backgrounds) ----
        media = [(n, zf.getinfo(n).file_size) for n in names if n.startswith("ppt/media/")]
        media.sort(key=lambda x: -x[1])
        if args.media_dir and media:
            os.makedirs(args.media_dir, exist_ok=True)
            for n, _ in media:
                with open(os.path.join(args.media_dir, os.path.basename(n)), "wb") as f:
                    f.write(zf.read(n))
        if args.logo and media:
            pick = media[0][0]
            if args.logo_name:
                match = [n for n, _ in media if os.path.basename(n) == args.logo_name
                         or n == args.logo_name]
                if match:
                    pick = match[0]
            with open(args.logo, "wb") as f:
                f.write(zf.read(pick))
            logo_pick = pick

    # ---- derive deck variables ----
    accents = [scheme[f"accent{i}"] for i in range(1, 7) if scheme.get(f"accent{i}")]
    a1 = accents[0] if accents else (scheme.get("hlink") or "48A9A")
    # pick a contrasting second accent: saturated, farthest in hue from a1
    def huedist(c):
        d = abs(_hue(c) - _hue(a1))
        return min(d, 360 - d)
    a2 = a1
    if len(accents) > 1:
        cand2 = [c for c in accents[1:] if _sat(c) > 0.3] or accents[1:]
        a2 = max(cand2, key=huedist)
    # map accent palette onto the deck's named hues by nearest hue
    HUES = {"blue": 215, "teal": 170, "green": 140, "amber": 45, "red": 5, "violet": 285}
    named = {}
    for k, target in HUES.items():
        cand = [c for c in accents if _sat(c) > 0.18] or accents
        if cand:
            named[k] = min(cand, key=lambda c: min(abs(_hue(c) - target),
                                                   360 - abs(_hue(c) - target)))
    dk = scheme.get("dk2") or scheme.get("dk1") or "111317"
    lt = scheme.get("lt1") or "FFFFFF"

    if args.light:
        bg, bg2 = lt, _mix(lt, "000000", .03)
        panel, panel2 = _mix(lt, "000000", .05), _mix(lt, "000000", .08)
        line, line2 = _mix(lt, "000000", .14), _mix(lt, "000000", .22)
        ink = scheme.get("dk1") or "1A1A1A"
        ink2, ink3 = _mix(ink, lt, .35), _mix(ink, lt, .55)
    else:
        base = dk if _lum(dk) < 0.18 else _mix(dk, "000000", .55)
        bg, bg2 = base, _mix(base, "FFFFFF", .04)
        panel, panel2 = _mix(base, "FFFFFF", .08), _mix(base, "FFFFFF", .12)
        line, line2 = _mix(base, "FFFFFF", .16), _mix(base, "FFFFFF", .24)
        ink = lt if _lum(lt) > 0.7 else "ECECEC"
        ink2, ink3 = _mix(ink, base, .35), _mix(ink, base, .55)

    def hexc(h):
        return "#" + h.lower() if h else "#888888"

    root = []
    root.append("/* THEME — extracted from {} ({} preset) */".format(
        os.path.basename(args.pptx), "light" if args.light else "dark"))
    root.append(":root{")
    root.append("  --bg:{}; --bg2:{}; --panel:{}; --panel2:{};".format(
        hexc(bg), hexc(bg2), hexc(panel), hexc(panel2)))
    root.append("  --line:{}; --line2:{};".format(hexc(line), hexc(line2)))
    root.append("  --ink:{}; --ink2:{}; --ink3:{};".format(hexc(ink), hexc(ink2), hexc(ink3)))
    hue_line = "  " + " ".join(
        "--{}:{};".format(k, hexc(named.get(k))) for k in HUES if named.get(k))
    root.append(hue_line)
    # --cyan / --mag are referenced by the template's graph node classes; alias them
    root.append("  --cyan:{}; --mag:{};".format(
        hexc(named.get("teal") or a1), hexc(named.get("violet") or a2)))
    root.append("  --accent:{}; --accent2:{};".format(hexc(a1), hexc(a2)))
    # font vars (brand faces with a substitute fallback for the model to wire up)
    def fontvar(name, label):
        if not name:
            return None
        sub = FONT_SUB.get(name.strip().lower(), name)
        return "  --font-{}:'{}', '{}', system-ui, sans-serif;  /* PPTX {}: {} */".format(
            label, name, sub, label, name)
    for fv in (fontvar(major, "head"), fontvar(minor, "body")):
        if fv:
            root.append(fv)
    root.append("  --mono:'JetBrains Mono', ui-monospace, Consolas, monospace;")
    root.append("}")
    block = "\n".join(root)

    # ---- report ----
    print("=" * 64)
    print("PowerPoint theme extracted:", os.path.basename(args.pptx))
    print("=" * 64)
    if w_in:
        ratio = w_in / h_in
        shape = "16:9" if abs(ratio - 16/9) < .05 else "4:3" if abs(ratio - 4/3) < .05 else f"{ratio:.2f}:1"
        px = "1280x720" if shape == "16:9" else "960x720" if shape == "4:3" else f"{round(h_in*ratio*96)}x{round(h_in*96)}"
        print(f"Slide size : {w_in:.2f}in x {h_in:.2f}in  ({shape})  -> set #canvas to {px}")
    print(f"Major font : {major or '-'}   Minor font : {minor or '-'}")
    print("Colour scheme:")
    for k in ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3",
              "accent4", "accent5", "accent6", "hlink"):
        if scheme.get(k):
            print(f"   {k:8s} #{scheme[k].lower()}")
    if media:
        print("Media (largest first). NOTE: the largest is usually a background photo;")
        print("the logo is typically a smaller, transparent PNG — INSPECT before choosing.")
        for n, sz in media[:10]:
            print(f"   {sz:>8d}  {n}")
        print("   (use --media-dir DIR to dump all, then --logo-name image3.png to grab the mark)")
        if args.logo:
            print(f"   -> extracted {logo_pick} to {args.logo}")
        if args.media_dir:
            print(f"   -> extracted all {len(media)} images to {args.media_dir}/")
    print("-" * 64)
    print(block)

    if args.out:
        with open(args.out, "w") as f:
            f.write(block + "\n")
        print("-" * 64)
        print("Wrote :root block to", args.out)

if __name__ == "__main__":
    main()
