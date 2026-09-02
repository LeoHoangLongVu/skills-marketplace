#!/usr/bin/env python3
r"""Strip a PowerPoint deck down to its TEMPLATE — blank branded slides to fill yourself.

The recurring DESIGN of a deck (logos, colour bands, backgrounds, footers) is whatever
appears, unchanged, on slide after slide; the CONTENT (titles, body, diagrams) is unique to
each slide. This removes every shape whose signature (position + size + text) does NOT recur
across slides, then renders the blanked slides and emits one self-contained HTML deck of
blank branded slides, each with an empty `.content` layer for your own content.

The editing and rendering happen INSIDE LibreOffice via UNO — the deck is never round-tripped
through Python's zip. That matters: re-packing a PowerPoint .pptx with Python (zipfile /
ElementTree / python-pptx) makes LibreOffice mis-scale grouped vector logos and text
(anisotropic squash), even with byte-identical content. Driving LibreOffice's own model
avoids that entirely, so SVG logos and text render exactly as PowerPoint intends.

Usage:
  python3 pptx_chrome.py INPUT.pptx -o template.html         # blank template deck (any .pptx)
  python3 pptx_chrome.py INPUT.pptx -o out.html --keep-dupes # keep visually identical layouts
  python3 pptx_chrome.py INPUT.pptx -o out.html \            # custom template: tune the header
      --logo-box 0.64,0.07,0.80,0.16 --logo-file white_logo.png
  python3 pptx_chrome.py INPUT.pptx -o out.html --logo-fix off  # skip header-logo repair
  python3 pptx_chrome.py INPUT.pptx -o out.html --thr 0.4       # stricter "recurring" cutoff

Works on any deck. The header-logo repair (and its --logo-* options) only triggers when a
deck has a coloured top band over a white body and a wide transparent wordmark in its media;
otherwise it is a no-op, so other templates pass through untouched.

Pipeline: LibreOffice/UNO (strip shapes + export PDF) -> pdftoppm (->png) -> HTML.
Requires: libreoffice/soffice with UNO (python3 `import uno`), pdftoppm (poppler-utils), Pillow.
"""
import argparse, base64, hashlib, io, os, re, subprocess, sys, tempfile, time
from PIL import Image

def have(cmd):
    return bool(subprocess.run(["bash", "-lc", f"command -v {cmd}"],
                               capture_output=True, text=True).stdout.strip())

def slide_size(src):
    import zipfile
    with zipfile.ZipFile(src) as z:
        try:
            xml = z.read("ppt/presentation.xml").decode("utf-8")
        except KeyError:
            return 1280, 720
    m = re.search(r'<p:sldSz[^>]*cx="(\d+)"[^>]*cy="(\d+)"', xml)
    if not m:
        return 1280, 720
    cx, cy = int(m.group(1)), int(m.group(2))
    return 1280, round(1280 * cy / cx)

def _soffice_bin():
    for p in ("/usr/lib/libreoffice/program/soffice", "/usr/bin/soffice", "/usr/bin/libreoffice"):
        if os.path.exists(p):
            return p
    found = subprocess.run(["bash", "-lc", "command -v soffice libreoffice | head -1"],
                           capture_output=True, text=True).stdout.strip()
    return found or None

def blank_to_pdf_via_uno(src, pdf_out, workdir, thr_frac=0.25):
    """Open src in LibreOffice (UNO), remove shapes whose (pos,size,text) signature does not
    recur on >= thr_frac of slides, and export to pdf_out. Returns kept-signature count."""
    try:
        import uno
        from com.sun.star.beans import PropertyValue
    except ImportError:
        sys.exit("python3 cannot 'import uno' — install the LibreOffice Python-UNO bridge")
    soffice = _soffice_bin()
    if not soffice:
        sys.exit("libreoffice/soffice not found")

    port = "2079"
    profile = "file://" + os.path.join(workdir, "uno_profile")
    proc = subprocess.Popen(
        [soffice, "-env:UserInstallation=" + profile, "--headless", "--invisible",
         "--nologo", "--norestore", "--nofirststartwizard",
         "--accept=socket,host=localhost,port=%s;urp;" % port],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def pv(name, value):
        p = PropertyValue(); p.Name = name; p.Value = value; return p

    desktop = doc = None
    try:
        lc = uno.getComponentContext()
        resolver = lc.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", lc)
        ctx = None
        for _ in range(60):
            try:
                ctx = resolver.resolve(
                    "uno:socket,host=localhost,port=%s;urp;StarOffice.ComponentContext" % port)
                break
            except Exception:
                time.sleep(0.5)
        if ctx is None:
            sys.exit("could not connect to LibreOffice UNO socket")
        smgr = ctx.ServiceManager
        desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        doc = desktop.loadComponentFromURL(
            uno.systemPathToFileUrl(os.path.abspath(src)), "_blank", 0, (pv("Hidden", True),))

        def sig(sh):
            p, s = sh.Position, sh.Size
            t = ""
            try:
                t = sh.getString().strip()[:24]
            except Exception:
                pass
            return (round(p.X / 100), round(p.Y / 100),
                    round(s.Width / 100), round(s.Height / 100), t)

        pages = doc.DrawPages
        n = pages.Count
        counts = {}
        for i in range(n):
            pg = pages.getByIndex(i)
            for j in range(pg.Count):
                k = sig(pg.getByIndex(j))
                counts[k] = counts.get(k, 0) + 1
        thr = max(3, round(thr_frac * n))
        keep = {k for k, c in counts.items() if c >= thr}

        for i in range(n):
            pg = pages.getByIndex(i)
            for j in range(pg.Count - 1, -1, -1):       # iterate backwards while removing
                sh = pg.getByIndex(j)
                if sig(sh) not in keep:
                    pg.remove(sh)

        doc.storeToURL(uno.systemPathToFileUrl(os.path.abspath(pdf_out)),
                       (pv("FilterName", "impress_pdf_Export"),))
        return len(keep)
    finally:
        try:
            if doc:
                doc.close(False)
        except Exception:
            pass
        try:
            if desktop:
                desktop.terminate()
        except Exception:
            pass
        try:
            proc.terminate()
        except Exception:
            pass

# LibreOffice stretches the SVG "FPT Software" header logo to its (wide) group box, which
# renders it squashed vs PowerPoint. We re-composite the deck's own transparent FPT logo
# (knocked out to white) at the geometry PowerPoint uses. Box fractions calibrated to the
# FPT/ebmpapst corporate master; the logo is auto-detected so re-runs on that series work.
FPT_BOX = (0.636, 0.070, 0.799, 0.161)

def _white_logo_from_deck(src):
    """Find a transparent, wide (aspect ~3) multi-colour logo in the deck and knock it out to
    white (coloured tiles -> white, white cut-out letters -> transparent). Returns RGBA or None."""
    import zipfile
    try:
        with zipfile.ZipFile(src) as z:
            for n in z.namelist():
                if not (n.startswith("ppt/media/") and n.lower().endswith(".png")):
                    continue
                try:
                    im = Image.open(io.BytesIO(z.read(n))).convert("RGBA")
                except Exception:
                    continue
                if im.getchannel("A").getextrema()[0] > 10:   # needs transparency
                    continue
                bb = im.getbbox()
                if not bb:
                    continue
                cw, ch = bb[2] - bb[0], bb[3] - bb[1]
                if ch == 0 or not (2.4 < cw / ch < 3.6):       # wide wordmark
                    continue
                px = im.crop(bb); d = px.load()
                for y in range(px.height):
                    for x in range(px.width):
                        r, g, b, a = d[x, y]
                        if a < 8:
                            continue
                        d[x, y] = (0, 0, 0, 0) if (r > 225 and g > 225 and b > 225) else (255, 255, 255, a)
                return px
    except Exception:
        return None
    return None

def fix_header_logo(png_path, logo, box=FPT_BOX):
    """If this page has a coloured top band over a white body (a content slide), re-composite
    the white logo at `box` (x0,y0,x1,y1 fractions), erasing LibreOffice's squashed copy first."""
    if logo is None:
        return
    from PIL import ImageDraw
    im = Image.open(png_path).convert("RGBA"); W, H = im.size
    rgb = im.convert("RGB")
    r, g, b = rgb.getpixel((int(W * 0.02), int(H * 0.05)))
    band = (r + g + b) < 740 and not (r > 235 and g > 235 and b > 235)   # top band is not white
    r2, g2, b2 = rgb.getpixel((int(W * 0.5), int(H * 0.5)))
    body_white = r2 > 235 and g2 > 235 and b2 > 235
    if not (band and body_white):
        return
    fill = rgb.getpixel((int(W * 0.02), int(H * 0.08)))                  # band colour to erase with
    x0, y0, x1, y1 = (round(box[0] * W), round(box[1] * H),
                      round(box[2] * W), round(box[3] * H))
    ImageDraw.Draw(im).rectangle([x0 - 12, y0 - 14, x1 + 14, y1 + 14], fill=fill)
    im.alpha_composite(logo.resize((x1 - x0, y1 - y0)), (x0, y0))
    im.convert("RGB").save(png_path)

def pdf_to_pngs(pdf, workdir):
    if not have("pdftoppm"):
        sys.exit("pdftoppm not found (install poppler-utils)")
    subprocess.run(["pdftoppm", "-png", "-r", "192", pdf, os.path.join(workdir, "pg")],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return sorted(os.path.join(workdir, f) for f in os.listdir(workdir)
                  if f.startswith("pg") and f.endswith(".png"))

def encode_bg(img, maxw=2560, q=92):
    """Crisp template background: PNG for flat slides (text stays sharp — JPEG rings around
    text on flat colour), high-quality JPEG only for photographic slides. Kept at ~2x the
    1280 canvas (maxw 2560) so the baked-in logo/chrome stays sharp when the deck is shown
    fullscreen above 1280px; smaller backgrounds visibly pixelate the header logo."""
    if img.width > maxw:
        img = img.resize((maxw, round(maxw * img.height / img.width)))
    img = img.convert("RGB")
    colors = img.resize((64, 36)).getcolors(maxcolors=2000)   # None if very colourful (photo)
    buf = io.BytesIO()
    if colors is not None:
        img.save(buf, "PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    img.save(buf, "JPEG", quality=q)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

TEMPLATE = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Blank Template Deck</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
html,body{height:100%;overflow:hidden;background:#000;font-family:'Lato','Segoe UI',Arial,sans-serif;}
#stage{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:#000;}
#canvas{width:__CW__px;height:__CH__px;position:relative;flex:none;transform-origin:center center;background:#fff;overflow:hidden;}
.slide{position:absolute;inset:0;opacity:0;visibility:hidden;}
.slide.active{opacity:1;visibility:visible;}
.slide .bg{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;}
/* Put your own content inside .content — it sits ABOVE the template background. */
.content{position:absolute;inset:0;}
#counter{position:fixed;right:14px;bottom:12px;color:#999;font-size:12px;}
</style></head>
<body><div id="stage"><div id="canvas">
__SLIDES__
</div></div>
<div id="counter"><b>1</b> / <span id="total">0</span></div>
<script>(function(){
  var slides=[].slice.call(document.querySelectorAll('.slide'));
  var n=slides.length,i=0;
  var c=document.getElementById('canvas');
  document.getElementById('total').textContent=n;
  function r(){slides.forEach(function(x,k){x.classList.toggle('active',k===i);});
    document.querySelector('#counter b').textContent=i+1;}
  function fit(){c.style.transform='scale('+Math.min(innerWidth/__CW__,innerHeight/__CH__)+')';}
  addEventListener('resize',fit);fit();
  addEventListener('keydown',function(e){
    if(e.key==='ArrowRight'||e.key===' '){i=Math.min(n-1,i+1);r();}
    else if(e.key==='ArrowLeft'){i=Math.max(0,i-1);r();}});
  document.getElementById('stage').addEventListener('click',function(e){
    if(e.clientX<innerWidth/2)i=Math.max(0,i-1);else i=Math.min(n-1,i+1);r();});
  r();
})();</script>
</body></html>'''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--keep-dupes", action="store_true",
                    help="keep layouts that render identically instead of deduping")
    ap.add_argument("--quality", type=int, default=92,
                    help="JPEG quality for photographic slides (flat slides use lossless PNG)")
    ap.add_argument("--thr", type=float, default=0.25,
                    help="recurrence threshold: keep shapes on >= this fraction of slides (default 0.25)")
    ap.add_argument("--logo-fix", choices=["auto", "off"], default="auto",
                    help="repair a header SVG logo squashed by LibreOffice (default auto)")
    ap.add_argument("--logo-file",
                    help="white logo PNG to composite on content slides (else auto-detected from the deck)")
    ap.add_argument("--logo-box", default=",".join(map(str, FPT_BOX)),
                    help='logo placement as "x0,y0,x1,y1" slide fractions '
                         '(default calibrated to the FPT/ebmpapst master)')
    args = ap.parse_args()
    if not os.path.exists(args.pptx):
        sys.exit("not found: " + args.pptx)
    src = os.path.abspath(args.pptx)
    try:
        logo_box = tuple(float(v) for v in args.logo_box.split(","))
        assert len(logo_box) == 4
    except Exception:
        sys.exit('--logo-box must be "x0,y0,x1,y1" fractions, e.g. 0.636,0.07,0.799,0.161')

    with tempfile.TemporaryDirectory() as wd:
        pdf = os.path.join(wd, "blank.pdf")
        kept = blank_to_pdf_via_uno(src, pdf, wd, thr_frac=args.thr)
        if not os.path.exists(pdf):
            sys.exit("LibreOffice/UNO did not produce a PDF")
        pngs = pdf_to_pngs(pdf, wd)
        if not pngs:
            sys.exit("no pages rendered")

        # Repair a squashed SVG header logo on content slides (see _white_logo_from_deck).
        if args.logo_fix == "auto":
            if args.logo_file:
                logo = Image.open(args.logo_file).convert("RGBA")
            else:
                logo = _white_logo_from_deck(src)
            if logo is not None:
                for p in pngs:
                    fix_header_logo(p, logo, box=logo_box)

        # Canvas aspect from the ACTUAL rendered pixels (never squish to fit).
        pw, ph = Image.open(pngs[0]).size
        CW, CH = 1280, round(1280 * ph / pw)

        last = len(pngs) - 1
        uniques, seen = [], {}
        for idx, p in enumerate(pngs):
            img = Image.open(p)
            key = hashlib.md5(img.resize((160, 90)).convert("RGB").tobytes()).hexdigest()
            if not args.keep_dupes and key in seen:
                seen[key]["pages"].append(idx)
                continue
            seen[key] = {"img": img, "first": idx, "pages": [idx]}
            uniques.append(key)

        # three roles: cover (opening), slide (body content), end (closing)
        items = []
        for key in uniques:
            u = seen[key]
            role = "cover" if u["first"] == 0 else "end" if last in u["pages"] else "slide"
            items.append((role, encode_bg(u["img"], q=args.quality)))

        sections = "\n".join(
            f'  <!-- {role} -->\n  <section class="slide" data-role="{role}"><img class="bg" src="{u}">'
            f'<div class="content"></div></section>' for role, u in items)
        html = (TEMPLATE.replace("__CW__", str(CW)).replace("__CH__", str(CH))
                .replace("__SLIDES__", sections))
        with open(args.out, "w") as f:
            f.write(html)

    roles = [r for r, _ in items]
    print(f"kept {kept} recurring shapes; {len(pngs)} slides -> {len(items)} unique blank "
          f"template(s)  ({CW}x{CH})  ->  {args.out}")
    print("Roles (deck order): " + ", ".join(f"#{i+1} {r}" for i, r in enumerate(roles)))
    print("Each <section data-role=...> is cover / slide / end; "
          "add your content inside its empty .content layer.")

if __name__ == "__main__":
    main()
