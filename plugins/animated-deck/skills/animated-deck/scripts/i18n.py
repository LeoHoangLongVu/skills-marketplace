#!/usr/bin/env python3
r"""i18n.py — translate a finished deck without touching its markup.

The deck is one self-contained .html; a translator (comtor) should never have to edit HTML.
This externalises every translatable string into a flat JSON keyed by a stable id, so the
comtor edits only values, and re-bakes the JSON back into a new single-file deck.

Workflow:
  1. key    — tag translatable text nodes with data-i18n="sNNN" and emit strings.<lang>.json
  2. (comtor copies strings.en.json -> strings.vi.json, translates the VALUES only)
  3. apply  — inject a strings file back into the keyed deck -> a new single-file deck

  python3 scripts/i18n.py key   deck.html -o deck.keyed.html --strings strings.en.json
  python3 scripts/i18n.py extract deck.keyed.html -o strings.en.json   # re-dump current text
  python3 scripts/i18n.py apply deck.keyed.html strings.vi.json -o deck.vi.html

What counts as translatable: visible prose in headings, paragraphs, list items, table cells,
captions, leaf <div>s, and SVG <text> (diagram labels). What is left ALONE: anything inside
<pre>/<code>/<script>/<style>, and any node whose text is purely a technical token (a file
name, path, or identifier with no real words) — so `deck.pptx`, `/animated-deck`, `.html` are
never offered for translation. Inline tags inside a string (<code>, <b>, <a>) are preserved;
the comtor translates the words around them and keeps the tags.

Notes
- `key` is idempotent: nodes already carrying data-i18n keep their key.
- strings.json preserves insertion order (document order), so it reads top-to-bottom.
- After `apply`, re-render: scripts/shot.sh deck.vi.html 1 <n> — a too-long translation can
  overflow a slide (the one thing this cannot prevent; split or shorten the source string).
- Diagram geometry is unaffected; only <text> contents change. Re-run check_diagram.js if a
  label grew a lot.
"""
import argparse, json, re, sys
from html.parser import HTMLParser

INLINE = {"a","b","i","em","strong","code","span","br","sup","sub","u","small","mark","tspan","abbr"}
VOID = {"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}
TEXT_TAGS = {"h1","h2","h3","h4","p","li","td","th","div","text","figcaption","caption"}
OPAQUE = {"pre","code","script","style"}      # never look inside these
# a candidate is a leaf only if it contains no child element outside INLINE
def is_block(tag): return tag not in INLINE

class Collector(HTMLParser):
    def __init__(self, src):
        super().__init__(convert_charrefs=False)
        self.src = src
        self.line_off = [0]
        for ln in src.split("\n"):
            self.line_off.append(self.line_off[-1] + len(ln) + 1)
        self.stack = []          # (tag, open_lt_off, inner_start, attrs_str)
        self.elements = []       # dict per closed element
        self.opaque_zones = []   # (start,end) char ranges to never key inside
        self._opaque_stack = []
    def _off(self):
        ln, col = self.getpos()
        return self.line_off[ln-1] + col
    def handle_starttag(self, tag, attrs):
        lt = self._off()
        gt = self.src.index(">", lt)
        inner = gt + 1
        self.stack.append((tag, lt, inner, self.src[lt:inner]))
        if tag in OPAQUE: self._opaque_stack.append(lt)
    def handle_startendtag(self, tag, attrs):
        pass  # self-closing: no inner text
    def handle_endtag(self, tag):
        lt = self._off()
        # pop matching tag
        for i in range(len(self.stack)-1, -1, -1):
            if self.stack[i][0] == tag:
                t, open_lt, inner_start, attrs_str = self.stack.pop(i)
                close_end = self.src.index(">", lt) + 1
                self.elements.append(dict(tag=t, open_lt=open_lt, inner_start=inner_start,
                                          inner_end=lt, close_end=close_end, attrs=attrs_str))
                break
        if tag in OPAQUE and self._opaque_stack:
            start = self._opaque_stack.pop()
            self.opaque_zones.append((start, self.src.index(">", lt)+1))

def parse(src):
    c = Collector(src); c.feed(src); c.close()
    return c.elements, c.opaque_zones

STRIP = re.compile(r"<[^>]+>")
ENT = re.compile(r"&[a-zA-Z#0-9]+;")
def visible(inner):
    t = ENT.sub(" ", STRIP.sub("", inner))
    return t
def translatable(inner):
    v = visible(inner).strip()
    if not re.search(r"[A-Za-zÀ-ỹ]", v):           # no real letters (numbers/symbols only)
        return False
    only = inner.strip()
    if only.startswith("<code") and only.endswith("</code>"):   # pure code chip
        return False
    # purely a technical token: a single word that looks like a path / filename /
    # identifier (carries / . _ : \). A plain word ("Content", "Template", "Output")
    # is real prose and stays translatable, even with no spaces.
    if " " not in v and re.search(r"[/._:\\]", v):
        return False
    return True

def get_key(attrs):
    m = re.search(r'data-i18n="([^"]+)"', attrs)
    return m.group(1) if m else None

# ---- tree with source offsets, incl. text nodes (for plain-text-run keying) ----
class TreeBuilder(HTMLParser):
    def __init__(self, src):
        super().__init__(convert_charrefs=False)
        self.src = src
        self.line_off=[0]
        for ln in src.split("\n"): self.line_off.append(self.line_off[-1]+len(ln)+1)
        self.root={"tag":"#root","children":[],"open_lt":0,"inner_start":0}
        self.stack=[self.root]
    def _off(self):
        ln,col=self.getpos(); return self.line_off[ln-1]+col
    def handle_starttag(self, tag, attrs):
        lt=self._off(); gt=self.src.index(">",lt)
        el={"tag":tag,"open_lt":lt,"inner_start":gt+1,"attrs":self.src[lt:gt+1],"children":[]}
        if tag in VOID:                                  # <img>, <br>, … never get an end tag
            el["void"]=True; el["inner_end"]=gt+1
            self.stack[-1]["children"].append(el)
        else:
            self.stack[-1]["children"].append(el); self.stack.append(el)
    def handle_startendtag(self, tag, attrs):
        lt=self._off(); gt=self.src.index(">",lt)
        self.stack[-1]["children"].append({"tag":tag,"open_lt":lt,"inner_start":gt+1,
            "attrs":self.src[lt:gt+1],"children":[],"void":True,"inner_end":gt+1})
    def handle_endtag(self, tag):
        lt=self._off()
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i]["tag"]==tag:
                el=self.stack[i]; el["inner_end"]=lt; el["close_end"]=self.src.index(">",lt)+1
                del self.stack[i:]; break
    def handle_data(self, data):
        if not data.strip() and "\n" in data and data.strip("\n\t ")=="":
            pass
        s=self._off()
        self.stack[-1]["children"].append({"text":data,"start":s,"end":s+len(data)})

def cmd_key(a):
    src = open(a.deck, encoding="utf-8").read()
    # strip any pre-existing keys so re-keying is clean and deterministic (avoids double-keying
    # a deck that was keyed by an earlier run / version)
    src = re.sub(r'\s+data-i18n="[^"]*"', '', src)
    tb=TreeBuilder(src); tb.feed(src); tb.close()
    used=set(); nextn=[0]
    def fresh():
        while True:
            nextn[0]+=1; k=f"s{nextn[0]:03d}"
            if k not in used: used.add(k); return k
    edits=[]; order=[]   # (pos,key) in document order for strings ordering
    def is_el(c): return "tag" in c
    def walk(el, opaque, insvg):
        op = opaque or el["tag"] in OPAQUE
        sv = insvg or el["tag"]=="svg"
        elem_children=[c for c in el["children"] if is_el(c)]
        if el["tag"]!="#root" and not elem_children and not el.get("void"):
            if not op:
                inner=src[el["inner_start"]:el["inner_end"]]
                if el["tag"] not in ("html","body") and translatable(inner):
                    k=get_key(el["attrs"]) or fresh()
                    if not get_key(el["attrs"]):
                        gt=src.rindex(">",el["open_lt"],el["inner_start"])
                        edits.append((gt,gt,f' data-i18n="{k}"'))
                    order.append((el["inner_start"],k,inner.strip()))
            return
        for c in el["children"]:
            if is_el(c): walk(c, op, sv)
            elif not op and not sv:
                m=re.match(r"^(\s*)([\s\S]*?)(\s*)$", c["text"])
                core=m.group(2)
                if core and translatable(core):
                    k=fresh()
                    rep=m.group(1)+f'<span data-i18n="{k}">'+core+"</span>"+m.group(3)
                    edits.append((c["start"],c["end"],rep))
                    order.append((c["start"],k,core.strip()))
    walk(tb.root, False, False)
    for s,e,txt in sorted(edits, key=lambda x:x[0], reverse=True):
        src = src[:s] + txt + src[e:]
    strings={k:v for _,k,v in sorted(order, key=lambda x:x[0])}
    out=a.out or a.deck.replace(".html",".keyed.html")
    open(out,"w",encoding="utf-8").write(src)
    sj=a.strings or "strings.en.json"
    json.dump(strings, open(sj,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    n=sum(1 for s,e,t in edits if "data-i18n" in t)
    print(f"keyed {len(strings)} strings -> {out}\nstrings -> {sj}")
    print("Translate the VALUES in the strings file, then: i18n.py apply", out, "strings.<lang>.json -o deck.<lang>.html")

def cmd_extract(a):
    src = open(a.deck, encoding="utf-8").read()
    els,_ = parse(src)
    strings = {}
    for e in sorted(els, key=lambda x:x["open_lt"]):
        k = get_key(e["attrs"])
        if k: strings[k] = src[e["inner_start"]:e["inner_end"]].strip()
    sj = a.out or "strings.json"
    json.dump(strings, open(sj,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"extracted {len(strings)} strings -> {sj}")

def cmd_apply(a):
    src = open(a.deck, encoding="utf-8").read()
    strings = json.load(open(a.strings, encoding="utf-8"))
    els,_ = parse(src)
    edits, miss = [], 0
    for e in els:
        k = get_key(e["attrs"])
        if not k: continue
        if k not in strings: miss += 1; continue
        edits.append((e["inner_start"], e["inner_end"], strings[k]))
    for s,en,val in sorted(edits, reverse=True):
        src = src[:s] + val + src[en:]
    out = a.out or a.deck.replace(".keyed.html",".out.html")
    open(out,"w",encoding="utf-8").write(src)
    print(f"applied {len(edits)} strings ({miss} keys missing from {a.strings}) -> {out}")

def main():
    ap = argparse.ArgumentParser(description="externalise/translate/re-bake deck text")
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("key");     k.add_argument("deck"); k.add_argument("-o","--out"); k.add_argument("--strings"); k.set_defaults(fn=cmd_key)
    x = sub.add_parser("extract"); x.add_argument("deck"); x.add_argument("-o","--out"); x.set_defaults(fn=cmd_extract)
    p = sub.add_parser("apply");   p.add_argument("deck"); p.add_argument("strings"); p.add_argument("-o","--out"); p.set_defaults(fn=cmd_apply)
    a = ap.parse_args(); a.fn(a)

if __name__ == "__main__":
    main()
