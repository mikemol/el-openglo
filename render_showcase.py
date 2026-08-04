#!/usr/bin/env python3
# [RECONSTRUCTED from this session's own tool calls — later compacted session, not on-disk
#  transcript. Faithful to the heredoc content. Verify before trusting as final.]
"""Real renderings of the segment displays in the EL Indiglo phosphor aesthetic:
lit segments bright, OFF segments faint ghost (present-but-not-active), on OLED void.
Every stroke thickened perpendicular (handles h/v/d uniformly) so diagonals render."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import math, segment_topology as ST

VOID="#080e14"; LIT="#a6d3ff"; GHOST="#2c3f52"; BLOOM="#a6d3ff"

def endpoints(spec):
    k=spec[0]
    if k=='h': return (spec[1],spec[3],spec[2],spec[3])
    if k=='v': return (spec[1],spec[2],spec[1],spec[3])
    if k=='d': return (spec[1][0],spec[1][1],spec[2][0],spec[2][1])

def quad(ax,ay,bx,by,hw,gap):
    dx,dy=bx-ax,by-ay; L=math.hypot(dx,dy) or 1e-9
    ux,uy=dx/L,dy/L; nx,ny=-uy,ux
    ax,ay=ax+ux*gap,ay+uy*gap; bx,by=bx-ux*gap,by-uy*gap
    return [(ax+nx*hw,ay+ny*hw),(bx+nx*hw,by+ny*hw),(bx-nx*hw,by-ny*hw),(ax-nx*hw,ay-ny*hw)]

def glyph_for(ch, fmt):
    u=ch.upper()
    for tbl in (ST.DIGITS16, ST.LETTERS16, ST.SYMBOLS16):
        if u in tbl:
            segs=set(tbl[u].split()) if tbl[u] else set()
            return ST.project(segs, fmt)
    return set()

def draw_char(ax, ch, fmt, x0, geom, show_ghost=True):
    lit=glyph_for(ch,fmt)
    for k,spec in geom.items():
        ex,ey,fx,fy=endpoints(spec)
        on = k in lit
        if not on and not show_ghost: continue
        hw = 0.115 if on else 0.075
        col= LIT if on else GHOST
        pts=[(x0+px, 5-py) for px,py in quad(ex,ey,fx,fy,hw,0.06)]
        if on:
            bpts=[(x0+px,5-py) for px,py in quad(ex,ey,fx,fy,hw*2.4,0.06)]
            ax.add_patch(Polygon(bpts, closed=True, fc=BLOOM, ec='none', alpha=0.16, zorder=1))
        ax.add_patch(Polygon(pts, closed=True, fc=col, ec='none', alpha=1.0 if on else 0.9, zorder=2))

def render(strings_fmts, title, path, show_ghost=True):
    rows=len(strings_fmts)
    fig,axes=plt.subplots(rows,1,figsize=(13, 1.9*rows), facecolor=VOID)
    if rows==1: axes=[axes]
    for ax,(label,s,fmt) in zip(axes, strings_fmts):
        geom = ST.GEOM22 if fmt in ("22",) else ST.GEOM16
        ax.set_facecolor(VOID)
        for i,ch in enumerate(s):
            draw_char(ax, ch, fmt, i*2.7, geom, show_ghost)
        ax.set_xlim(-0.4, len(s)*2.7); ax.set_ylim(-0.6,5.4)
        ax.set_aspect('equal'); ax.axis('off')
        ax.text(-0.3, 5.2, label, color="#5a7290", fontsize=9, family='monospace', va='top')
    fig.suptitle(title, color=LIT, fontsize=13, family='monospace', y=0.995)
    plt.tight_layout(); plt.savefig(path, facecolor=VOID, dpi=110, bbox_inches='tight'); plt.close()
    return path
