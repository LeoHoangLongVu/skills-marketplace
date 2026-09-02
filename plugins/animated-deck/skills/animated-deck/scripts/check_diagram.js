#!/usr/bin/env node
// check_diagram.js — static collision/geometry checker for animated-deck SVG diagrams.
//
//   node scripts/check_diagram.js deck.html
//
// For every <svg class="graph">, it reports problems that do NOT show up in source and
// are easy to miss without rendering:
//   - PADDING : text inside a node box closer than 14px to a side (horizontal)
//   - VCENTER : node text block not vertically centred (top vs bottom gap differ > 10px)
//   - OVERLAP : two node boxes overlap (a container that *holds* a child is allowed)
//   - TIP     : an arrowhead does not land on a node border (floats / overshoots)
//   - LABEL   : an arrow caption overlaps a node box, sits on a line, or grazes an elbow
//   - FONT    : any text below the readability floor (font-size < 14 on the 1280x720 canvas)
//
// It treats <rect> with width>=300 (or fill #0b0f18) as a "container" — overlaps with the
// boxes it encloses are expected and skipped. Tune CONTAINER_W if your wrappers are smaller.
//
// Exit code is non-zero if any issue is found, so it can gate a build.

const fs = require("fs");
const file = process.argv[2];
if (!file) { console.error("usage: check_diagram.js <deck.html>"); process.exit(2); }
const html = fs.readFileSync(file, "utf8");
const svgs = [...html.matchAll(/<svg class="graph[\s\S]*?<\/svg>/g)].map(m => m[0]);
const CHAR_W = 0.6;   // monospace width factor per font-size unit
const PAD_MIN = 14;   // min horizontal padding text->border
const VC_TOL = 10;    // max |topGap - bottomGap|
const SEG_CLEAR = 8;  // min label clearance to an orthogonal segment
const DIAG_CLEAR = 14;// min label clearance to a diagonal segment
const FONT_MIN = 14;  // hard floor for any text on the 1280x720 canvas (readability)

function rects(s) {
  return [...s.matchAll(/<rect\b[^>]*>/g)].map(t => {
    const g = a => { const m = t[0].match(new RegExp(a + '="([^"]*)"')); return m ? m[1] : null; };
    return { x:+g("x"), y:+g("y"), w:+g("width"), h:+g("height"), fill:g("fill")||"" };
  });
}
function encloses(R, Q) { return Q!==R && Q.x>=R.x && Q.y>=R.y && Q.x+Q.w<=R.x+R.w && Q.y+Q.h<=R.y+R.h; }
function groups(s) { return [...s.matchAll(/<g class="gn"[\s\S]*?<\/g>/g)].map(m => m[0]); }
function texts(block) {
  return [...block.matchAll(/<text[^>]*\bx="([\d.]+)"[^>]*\by="([\d.]+)"[^>]*\bfont-size="([\d.]+)"[^>]*>([^<]*)<\/text>/g)]
    .map(m => ({ cx:+m[1], by:+m[2], fs:+m[3], s:m[4] }));
}
function pathSegs(d) { // M/H/V chains only
  const out = []; let x=0,y=0;
  (d.match(/[MHV][^MHVZ]*/g) || []).forEach(t => {
    const k=t[0], n=t.slice(1).trim().split(/\s+/).map(Number);
    if (k==="M"){x=n[0];y=n[1];} else if (k==="H"){out.push([x,y,n[0],y]);x=n[0];} else if (k==="V"){out.push([x,y,x,n[0]]);y=n[0];}
  });
  return out;
}
function pathEnd(d){ let x=0,y=0; (d.match(/[MHV][^MHVZ]*/g)||[]).forEach(t=>{const k=t[0],n=t.slice(1).trim().split(/\s+/).map(Number); if(k==="M"){x=n[0];y=n[1];} else if(k==="H"){x=n[0];} else if(k==="V"){y=n[0];}}); return [x,y]; }

let problems = 0;
const labels = ["graph"];
svgs.forEach((s, si) => {
  const issues = [];
  const rs = rects(s);
  // a "container" is any box that encloses another box (cluster wrapper / pool)
  const isCont = r => rs.some(q => encloses(r, q));
  const nodeRects = rs.filter(r => !isCont(r));

  // node text padding + vertical centring
  groups(s).forEach(g => {
    const rm = g.match(/<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"/);
    if (!rm) return;
    const x=+rm[1], y=+rm[2], w=+rm[3], h=+rm[4];
    const ts = texts(g);
    ts.forEach(t => {
      const tw = t.s.length*CHAR_W*t.fs, l=t.cx-tw/2, r=t.cx+tw/2;
      if (l < x+PAD_MIN || r > x+w-PAD_MIN)
        issues.push(`PADDING "${t.s.slice(0,28)}" m[${(l-x).toFixed(0)},${(x+w-r).toFixed(0)}] box[${x},${x+w}]`);
    });
    if (ts.length && !isCont({x,y,w,h})) {
      const f0=ts[0], fl=ts[ts.length-1];
      const top=(f0.by-0.70*f0.fs)-y, bot=(y+h)-(fl.by+0.20*fl.fs);
      if (Math.abs(top-bot) > VC_TOL) issues.push(`VCENTER box[${x},${y}] top=${top.toFixed(0)} bot=${bot.toFixed(0)}`);
    }
  });

  // box overlaps (skip container-holds-child)
  for (let i=0;i<rs.length;i++) for (let j=i+1;j<rs.length;j++) {
    const a=rs[i], b=rs[j];
    const ox=Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x), oy=Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y);
    if (ox>0 && oy>0) {
      const aIn = a.x>=b.x&&a.y>=b.y&&a.x+a.w<=b.x+b.w&&a.y+a.h<=b.y+b.h;
      const bIn = b.x>=a.x&&b.y>=a.y&&b.x+b.w<=a.x+a.w&&b.y+b.h<=a.y+a.h;
      if (aIn||bIn) continue;
      issues.push(`OVERLAP [${a.x},${a.y}]&[${b.x},${b.y}] ${ox}x${oy}`);
    }
  }

  // segments (for tip + label checks)
  const segs = [];
  [...s.matchAll(/<line class="ge" x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)"/g)].forEach(m=>segs.push([+m[1],+m[2],+m[3],+m[4]]));
  [...s.matchAll(/<path class="ge" d="([^"]+)"/g)].forEach(m=>pathSegs(m[1]).forEach(g=>segs.push(g)));

  // arrowhead tips land on a node border
  const tips = [];
  [...s.matchAll(/<line class="ge"[^>]*x2="([\d.]+)" y2="([\d.]+)"[^>]*marker-end/g)].forEach(m=>tips.push([+m[1],+m[2]]));
  [...s.matchAll(/<path class="ge" d="([^"]+)"[^>]*marker-end/g)].forEach(m=>tips.push(pathEnd(m[1])));
  tips.forEach(([x,y]) => {
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;  // curved/seq edge the parser can't read — skip, don't false-flag
    const hit = rs.find(r =>
      ((Math.abs(x-r.x)<=2||Math.abs(x-(r.x+r.w))<=2) && y>=r.y-2 && y<=r.y+r.h+2) ||
      ((Math.abs(y-r.y)<=2||Math.abs(y-(r.y+r.h))<=2) && x>=r.x-2 && x<=r.x+r.w+2));
    if (!hit) issues.push(`TIP (${x},${y}) not on a node border`);
  });

  // labels vs boxes and vs segments
  [...s.matchAll(/<text class="glab[^>]*\bx="([\d.]+)"[^>]*\by="([\d.]+)"[^>]*\bfont-size="([\d.]+)"[^>]*>([^<]*)<\/text>/g)].forEach(m => {
    const l = { cx:+m[1], by:+m[2], fs:+m[3], s:m[4] };
    const hw=l.s.length*CHAR_W*l.fs/2, lx1=l.cx-hw, lx2=l.cx+hw, ly1=l.by-l.fs*0.85, ly2=l.by+l.fs*0.20;
    for (const r of nodeRects) {
      const ox=Math.min(lx2,r.x+r.w+2)-Math.max(lx1,r.x-2), oy=Math.min(ly2,r.y+r.h+2)-Math.max(ly1,r.y-2);
      if (ox>0&&oy>0){ issues.push(`LABEL "${l.s}" over box[${r.x},${r.y}]`); break; }
    }
    for (const [x1,y1,x2,y2] of segs) {
      if (y1===y2) { const xa=Math.min(x1,x2),xb=Math.max(x1,x2);
        if (lx2>xa && lx1<xb) { const overlapY=ly1<=y1&&ly2>=y1, d=Math.min(Math.abs(ly1-y1),Math.abs(ly2-y1)); if (overlapY||d<SEG_CLEAR){issues.push(`LABEL "${l.s}" on line y=${y1}`);break;} } }
      else if (x1===x2) { const ya=Math.min(y1,y2),yb=Math.max(y1,y2);
        if (ly2>ya && ly1<yb) { const overlapX=lx1<=x1&&lx2>=x1, d=Math.min(Math.abs(lx1-x1),Math.abs(lx2-x1)); if (overlapX||d<SEG_CLEAR){issues.push(`LABEL "${l.s}" on line x=${x1}`);break;} } }
      else { const A=y2-y1,B=x1-x2,C=-(A*x1+B*y1), d=Math.abs(A*l.cx+B*l.by+C)/Math.hypot(A,B); if (d<DIAG_CLEAR){issues.push(`LABEL "${l.s}" on diagonal`);break;} }
    }
  });

  // readability: no text below the font floor
  [...s.matchAll(/<text\b[^>]*\bfont-size="([\d.]+)"[^>]*>([^<]*)<\/text>/g)].forEach(m => {
    if (+m[1] < FONT_MIN) issues.push(`FONT "${m[2].slice(0,24)}" font-size=${m[1]} < ${FONT_MIN}`);
  });

  problems += issues.length;
  console.log(`svg${si}: ${issues.length ? "ISSUES\n  " + issues.join("\n  ") : "OK"}`);
});
process.exit(problems ? 1 : 0);
