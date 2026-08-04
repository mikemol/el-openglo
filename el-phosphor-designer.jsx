import { useState, useMemo, useRef, useCallback } from "react";

/* EL PHOSPHOR DESIGNER — the knob the watches never shipped.
   Advisory instrument: in-browser gates use Machado matrices (extracted from
   colorspacious) + Lab dE76. The gate of record is make_schemes.py
   (5 views, CAM02-UCS, per-view floors). Marginal readings say so. */

// ---------- color math (mirrors the verified Python pipeline exactly) ----------
const MACHADO = {
  protan: [[0.152286,1.052583,-0.204868],[0.114503,0.786281,0.099216],[-0.003882,-0.048116,1.051998]],
  deutan: [[0.367322,0.860646,-0.227968],[0.280085,0.672501,0.047413],[-0.01182,0.04294,0.968881]],
  tritan: [[1.255528,-0.076749,-0.178779],[-0.078411,0.930809,0.147602],[0.004733,0.691367,0.3039]],
};
const lin = (c) => c.map((v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
const toLab = ([r, g, b]) => {
  const X = 0.4124564*r+0.3575761*g+0.1804375*b, Y = 0.2126729*r+0.7151522*g+0.0721750*b, Z = 0.0193339*r+0.1191920*g+0.9503041*b;
  const f = (t) => (t > 0.008856 ? Math.cbrt(t) : 7.787*t + 16/116);
  const fx = f(X/0.95047), fy = f(Y), fz = f(Z/1.08883);
  return [116*fy-16, 500*(fx-fy), 200*(fy-fz)];
};
const applyM = (M, c) => M.map((row) => Math.min(1, Math.max(0, row[0]*c[0]+row[1]*c[1]+row[2]*c[2])));
const labViews = (rgb) => { const l = lin(rgb); return [toLab(l), ...Object.values(MACHADO).map((M) => toLab(applyM(M, l)))]; };
const dist = (a, b) => Math.hypot(a[0]-b[0], a[1]-b[1], a[2]-b[2]);
const viewDEs = (a, b) => { const va = labViews(a), vb = labViews(b); return va.map((v, i) => dist(v, vb[i])); };
const relLum = (c) => { const [r,g,b] = lin(c); return 0.2126*r+0.7152*g+0.0722*b; };
const wcag = (f, b) => { const [hi, lo] = [relLum(f), relLum(b)].sort((x,y)=>y-x); return (hi+0.05)/(lo+0.05); };
// per-view floors from the Okabe-Ito constellation, same pipeline
const OI = [[230,159,0],[86,180,233],[0,158,115],[240,228,66],[0,114,178],[213,94,0],[204,121,167]];
const FLOORS = (() => { const f = [1e9,1e9,1e9,1e9];
  for (let i=0;i<OI.length;i++) for (let j=i+1;j<OI.length;j++) viewDEs(OI[i],OI[j]).forEach((d,v)=>{ if(d<f[v]) f[v]=d; });
  return f; })();
const VIEW_NAMES = ["trichromat","protan","deutan","tritan"];
const qWorst = (a, b, factor=0.8) => { let best={q:1e9,view:""};
  viewDEs(a,b).forEach((d,i)=>{ const q=d/(FLOORS[i]*factor); if(q<best.q) best={q, view:VIEW_NAMES[i]}; }); return best; };

// ---------- hsl helpers ----------
const rgb2hsl = ([r,g,b]) => { r/=255; g/=255; b/=255;
  const mx=Math.max(r,g,b), mn=Math.min(r,g,b), l=(mx+mn)/2; if(mx===mn) return [0,0,l];
  const d=mx-mn, s=l>0.5?d/(2-mx-mn):d/(mx+mn);
  let h = mx===r ? (g-b)/d + (g<b?6:0) : mx===g ? (b-r)/d + 2 : (r-g)/d + 4;
  return [h*60, s, l]; };
const hsl2rgb = ([h,s,l]) => { h=((h%360)+360)%360/360;
  if(s===0){ const v=Math.round(l*255); return [v,v,v]; }
  const q=l<0.5?l*(1+s):l+s-l*s, p=2*l-q;
  const f=(t)=>{ t=((t%1)+1)%1; if(t<1/6) return p+(q-p)*6*t; if(t<1/2) return q; if(t<2/3) return p+(q-p)*(2/3-t)*6; return p; };
  return [f(h+1/3),f(h),f(h-1/3)].map((v)=>Math.round(v*255)); };
const hue = (c) => rgb2hsl(c)[0];
const css = (c) => `rgb(${c[0]},${c[1]},${c[2]})`;

// ---------- canonical token shapes (openglo, base hue 172) ----------
const BASE_HUE = 172;
const PHOSPHOR_OFF = { view:[6,11,13], view_alt:[10,18,20], window:[12,21,23], window_alt:[10,19,21],
  button:[18,34,37], button_alt:[16,30,33], fg:[140,232,218], fg_act:[168,255,242], fg_in:[61,102,96],
  focus:[0,224,194], hover:[26,165,147], sel_bg:[0,205,176], sel_alt:[0,180,155], sel_fg:[4,33,29], sel_in:[10,64,56] };
const PHOSPHOR_LIT = { view:[175,242,226], view_alt:[160,235,218], window:[157,230,213], window_alt:[147,222,204],
  button:[138,218,203], button_alt:[126,208,192], fg:[10,38,34], fg_act:[3,27,23], fg_in:[78,138,128],
  focus:[0,112,95], hover:[14,138,118], sel_bg:[11,31,28], sel_alt:[8,24,21], sel_fg:[124,243,223], sel_in:[78,138,128] };
const FIXED = {
  off: { neg:[255,110,99], neu:[255,180,84], pos:[85,240,160], link:[86,240,240], visited:[58,151,166],
         sel_link:[6,58,84], sel_vis:[12,66,74], sel_neg:[120,26,20], sel_neu:[110,66,8], sel_pos:[8,74,40] },
  lit: { neg:[166,35,24], neu:[138,90,10], pos:[7,102,53], link:[6,106,138], visited:[42,106,116],
         sel_link:[124,232,255], sel_vis:[140,200,210], sel_neg:[255,154,140], sel_neu:[255,204,133], sel_pos:[140,247,190] },
};
const SECTORS = { neg:[340,25], neu:[30,75], pos:[90,170], link:[180,270], visited:[180,310] };
const inSector = (h,[lo,hi]) => (lo>hi ? h>=lo||h<=hi : h>=lo&&h<=hi);

const derive = (knobHue, mode) => {
  const shape = mode==="lit" ? PHOSPHOR_LIT : PHOSPHOR_OFF, dH = knobHue-BASE_HUE, t = {};
  for (const k in shape) { const [h,s,l] = rgb2hsl(shape[k]); t[k] = hsl2rgb([h+dH, s, l]); }
  return { ...t, ...FIXED[mode==="lit"?"lit":"off"] };
};
const hue2nm = (h) => Math.round(h<=270 ? 700-(h/270)*320 : 380); // rough, labeled approximate

// ---------- seven-segment readout ----------
const SEG = { A:[0,0,"h"], G:[0,1,"h"], D:[0,2,"h"], F:[0,0,"v"], B:[1,0,"v"], E:[0,1,"v"], C:[1,1,"v"] };
const DIG = { 0:"ABCDEF",1:"BC",2:"ABGED",3:"ABGCD",4:"FGBC",5:"AFGCD",6:"AFGEDC",7:"ABC",8:"ABCDEFG",9:"ABCFGD" };
function SevenSeg({ value, on, off }) {
  const L=22, T=5, digits = String(value).padStart(3,"0").split("");
  const poly = (kind,ux,uy,lit) => { const g=T*0.7, h=T/2, a=g, b=L-g;
    let pts=[[a,0],[a+h,-h],[b-h,-h],[b,0],[b-h,h],[a+h,h]];
    if(kind==="v") pts=pts.map(([x,y])=>[y,x]);
    return pts.map(([x,y])=>`${x+ux*L},${y+uy*L}`).join(" ");
  };
  return (<svg width={digits.length*L*1.6+8} height={L*2+12} style={{display:"block"}} aria-hidden="true">
    {digits.map((d,i)=>(<g key={i} transform={`translate(${i*L*1.6+6},6) skewX(-5)`}>
      {Object.entries(SEG).map(([name,[ux,uy,kind]])=>(
        <polygon key={name} points={poly(kind,ux,uy)} fill={DIG[d].includes(name)?on:off}/>))}
    </g>))}
  </svg>);
}

// ---------- knob ----------
function Knob({ value, onChange, ring, face, tick }) {
  const ref = useRef(null);
  const drag = useCallback((e) => {
    const el = ref.current; if(!el) return;
    const r = el.getBoundingClientRect(), cx=r.left+r.width/2, cy=r.top+r.height/2;
    const move = (ev) => { const p = ev.touches?ev.touches[0]:ev;
      const a = Math.atan2(p.clientY-cy, p.clientX-cx)*180/Math.PI+90;
      onChange(Math.round(((a%360)+360)%360)); };
    const up = () => { window.removeEventListener("pointermove",move); window.removeEventListener("pointerup",up); };
    window.addEventListener("pointermove",move); window.addEventListener("pointerup",up); move(e);
  },[onChange]);
  return (<div ref={ref} onPointerDown={drag}
      style={{width:180,height:180,borderRadius:"50%",position:"relative",cursor:"grab",touchAction:"none",
        background:`conic-gradient(from 0deg, ${[0,60,120,180,240,300,360].map(h=>css(hsl2rgb([h,0.85,0.55]))+" "+(h/3.6)+"%").join(",")})`,
        boxShadow:`0 0 24px ${ring}55, inset 0 0 0 6px ${face}`}}>
    <div style={{position:"absolute",inset:14,borderRadius:"50%",background:face,
        boxShadow:`inset 0 2px 10px #00000088, 0 0 0 1px ${ring}44`}}/>
    <div style={{position:"absolute",inset:0,transform:`rotate(${value}deg)`}}>
      <div style={{position:"absolute",top:20,left:"50%",width:4,height:26,marginLeft:-2,borderRadius:2,
        background:tick,boxShadow:`0 0 10px ${tick}`}}/>
    </div>
  </div>);
}

// ---------- ledger row ----------
function Row({ label, value, unit, need, state, note, C }) {
  const color = state==="ok"?C.pos : state==="viol"?C.neg : state==="marg"?C.neu : C.ghost;
  const word = state==="ok"?"OK" : state==="viol"?"VIOLATION" : state==="marg"?"MARGINAL" : "surfaced";
  return (<div style={{display:"flex",gap:10,alignItems:"baseline",fontSize:12,padding:"3px 0",
      borderBottom:`1px solid ${css(C.raw.view_alt)}`}}>
    <span style={{width:150,color:css(C.raw.fg_in)}}>{label}</span>
    <span style={{width:110,color:css(C.raw.fg)}}>{value}{unit}{need?` / ${need}`:""}</span>
    <span style={{width:88,color:css(color),fontWeight:700,letterSpacing:1}}>{word}</span>
    <span style={{color:css(C.raw.fg_in),flex:1}}>{note||""}</span>
  </div>);
}

export default function PhosphorDesigner() {
  const [h, setH] = useState(BASE_HUE);
  const [mode, setMode] = useState("off");
  const [copied, setCopied] = useState(false);
  const T = useMemo(() => derive(h, mode), [h, mode]);
  const C = { raw:T, pos:T.pos, neg:T.neg, neu:T.neu, ghost:T.fg_in };

  const ledger = useMemo(() => {
    const rows = [];
    const wc = (label, f, b, need) => { const r = wcag(T[f], T[b]);
      rows.push({label, value:r.toFixed(2), unit:":1", need, state:r>=need?"ok":"viol"}); };
    wc("body / view", "fg", "view", 4.5); wc("body / button", "fg", "button", 4.5);
    wc("link / view", "link", "view", 4.5); wc("neg / view", "neg", "view", 4.5);
    wc("neu / view", "neu", "view", 4.5); wc("pos / view", "pos", "view", 4.5);
    wc("sel fg / bg", "sel_fg", "sel_bg", 4.5); wc("focus / button", "focus", "button", 3.0);
    rows.push({label:"ghost / view", value:wcag(T.fg_in,T.view).toFixed(2), unit:":1",
      state:"surf", note:"unlit segment: intentional"});
    const cv = (label, a, b, enforced) => { const {q,view} = qWorst(T[a], T[b]);
      const state = !enforced ? "surf" : q>=1.05?"ok" : q>=0.95?"marg" : "viol";
      rows.push({label, value:`q=${q.toFixed(2)}`, state,
        note: state==="marg" ? `worst: ${view} — certify with make_schemes.py` : `worst: ${view}`}); };
    cv("CVD neg~pos","neg","pos",true); cv("CVD neg~neu","neg","neu",true);
    cv("CVD neu~pos","neu","pos",true); cv("CVD link~body","link","fg",true);
    cv("CVD pos~accent","pos","focus",false); cv("CVD link~accent","link","focus",false);
    for (const slot in SECTORS) { const hh = hue(T[slot]);
      rows.push({label:`sector ${slot}`, value:`${Math.round(hh)}°`,
        need:`${SECTORS[slot][0]}–${SECTORS[slot][1]}`, state: inSector(hh,SECTORS[slot])?"ok":"viol"}); }
    const clash = Object.entries(SECTORS).find(([k,s])=>k!=="link"&&k!=="visited"&&inSector(h,s));
    if (clash) rows.push({label:"phosphor field", value:`${h}°`, state:"surf",
      note:`knob sits in the ${clash[0]} sector — expect accent collisions (declared overrides exist for this)`});
    return rows;
  }, [T, h]);

  const exportText = useMemo(() => {
    const name = `EL-Custom-${h}${mode==="lit"?"-Lit":""}`;
    const s3 = (c)=>`"${c.join(",")}"`;
    const keys = Object.keys(T).map((k)=>`${k}=${s3(T[k])}`).join(", ");
    return `# paste into make_schemes.py tables (advisory values — certify with the gate of record)\n`+
      `${name.replace(/-/g,"_").toUpperCase()} = dict(name="${name}", id="${name}", ${keys}, fx_dis=${s3(T.view)}, fx_in=${s3(T.view_alt)}, tt_is_sel=${mode==="lit"?"True":"False"})\n`+
      `# make_wallpaper.py VARIANTS entry\n"${name.toLowerCase()}": ("${css(T.view_alt)}", "${css(T.view)}", "${css(T.fg_in)}", "${css(T.fg)}", "${css(T.focus)}"),`;
  }, [T, h, mode]);

  const copy = () => { navigator.clipboard?.writeText(exportText).then(()=>{ setCopied(true); setTimeout(()=>setCopied(false),1500); }); };
  const P = (k)=>css(T[k]);

  return (<div style={{minHeight:"100vh",background:P("view"),color:P("fg"),
      fontFamily:"ui-monospace, 'Cascadia Mono', Menlo, monospace",padding:24,transition:"background .3s"}}>
    <div style={{maxWidth:880,margin:"0 auto"}}>
      <div style={{display:"flex",alignItems:"baseline",gap:14,marginBottom:6}}>
        <h1 style={{fontSize:17,letterSpacing:3,margin:0,color:P("fg_act")}}>EL PHOSPHOR DESIGNER</h1>
        <span style={{fontSize:11,color:P("fg_in")}}>advisory instrument — gate of record: make_schemes.py</span>
      </div>
      <div style={{display:"flex",gap:26,flexWrap:"wrap",alignItems:"flex-start"}}>
        {/* left: the knob */}
        <div style={{background:P("window"),padding:20,borderRadius:14,boxShadow:`0 0 0 1px ${P("view_alt")}`}}>
          <Knob value={h} onChange={setH} ring={P("focus")} face={P("window")} tick={P("focus")} />
          <input type="range" min={0} max={359} value={h} onChange={(e)=>setH(+e.target.value)}
            aria-label="phosphor hue" style={{width:180,marginTop:14,accentColor:P("focus")}}/>
          <div style={{display:"flex",alignItems:"center",gap:12,marginTop:10}}>
            <SevenSeg value={h} on={P("fg_act")} off={mode==="lit"?P("view_alt"):P("sel_in")}/>
            <div style={{fontSize:11,color:P("fg_in")}}>hue °<br/>≈{hue2nm(h)} nm</div>
          </div>
          <button onClick={()=>setMode(mode==="off"?"lit":"off")}
            style={{marginTop:14,width:"100%",padding:"10px 0",borderRadius:8,border:`1px solid ${P("focus")}`,
              background:mode==="lit"?P("sel_bg"):P("button"),color:mode==="lit"?P("sel_fg"):P("fg_act"),
              fontFamily:"inherit",letterSpacing:2,cursor:"pointer",fontSize:12}}>
            {mode==="lit" ? "◉ BACKLIGHT ON — release" : "○ BACKLIGHT OFF — hold"}
          </button>
        </div>
        {/* right: specimen + ledger */}
        <div style={{flex:1,minWidth:340}}>
          <div style={{background:P("window"),borderRadius:14,padding:"12px 16px",marginBottom:14,
              boxShadow:`0 0 0 1px ${P("view_alt")}`,fontSize:13,lineHeight:1.9}}>
            <div>Body text on the panel. <a href="#k" style={{color:P("link")}}>A link</a> and a <span style={{color:P("visited")}}>visited one</span>.</div>
            <div><span style={{background:P("sel_bg"),color:P("sel_fg"),padding:"1px 6px",borderRadius:3}}>selection presses the backlight</span>
              {"  "}<button style={{background:P("button"),color:P("fg"),border:`1px solid ${P("focus")}`,borderRadius:5,padding:"2px 10px",fontFamily:"inherit",fontSize:12}}>Button</button></div>
            <div><span style={{color:P("neg")}}>■ error</span>  <span style={{color:P("neu")}}>■ caution</span>  <span style={{color:P("pos")}}>■ success</span>  <span style={{color:P("fg_in")}}>■ ghost segments</span></div>
          </div>
          <div style={{background:P("window"),borderRadius:14,padding:"10px 16px",boxShadow:`0 0 0 1px ${P("view_alt")}`}}>
            <div style={{fontSize:11,letterSpacing:2,color:P("fg_in"),marginBottom:4}}>GATE LEDGER (live)</div>
            {ledger.map((r,i)=><Row key={i} {...r} C={C}/>)}
          </div>
          <div style={{marginTop:14}}>
            <textarea readOnly value={exportText} rows={5} style={{width:"100%",background:P("view_alt"),
              color:P("fg"),border:`1px solid ${P("focus")}44`,borderRadius:8,fontFamily:"inherit",fontSize:11,padding:10}}/>
            <button onClick={copy} style={{marginTop:6,padding:"6px 16px",borderRadius:6,cursor:"pointer",
              border:`1px solid ${P("focus")}`,background:P("button"),color:P("fg_act"),fontFamily:"inherit",fontSize:12}}>
              {copied?"copied":"copy generator entry"}</button>
          </div>
        </div>
      </div>
    </div>
  </div>);
}
