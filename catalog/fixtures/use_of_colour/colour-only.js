// A known-bad painter (W75): critical urgency is carried by hue alone and low urgency by opacity alone, with no
// weight, shape, text or animation cue. `opa_gate.py use_of_colour <this file> --expect denied:U1` must read DENIED.
function paint() {
    var u = root.urgencyAt(i);
    ctx.fillStyle = u === 2 ? hot : lit;
    ctx.globalAlpha = u === 0 ? 0.5 : 1.0;
    var grow = (run && run.bold) ? s / 2 : 0;
    ctx.fillRect(x - grow, y - grow, s + 2 * grow, s + 2 * grow);
}
