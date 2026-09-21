// marquee-body.js — a notification body's markup, parsed to plain text + style runs.
// Shipped beside the marquee's main.qml (which imports it by bare name) and run
// headless by scripts/check_marquee_body.py on synthetic bodies — the same code.
//
// ⚑ BODIES ARE MARKUP (W39). The freedesktop notification spec allows <b> <i>
// <u> <a href> <img src alt> in a body and says a server that does not support
// them "should filter them out"; Plasma's model passes its sanitised subset
// through, with <br> and entities. Un-stripped, the TAGS scrolled across the
// board as text. parseBody() returns the plain text plus STYLE RUNS — spans of
// bold / italic / underline / link / colour over the text — so the styling half
// (bold -> lit weight or glow; a sender colour -> a hue on the lit token, gated
// by the palette's floors — catalog/relations.md §5) has its data when its
// relation is applied. Until then only the text is read.
.pragma library

function parseBody(html) {
    var text = "", runs = [];
    var st = { b: 0, i: 0, u: 0, a: "", color: "" };
    var i = 0, n = html.length;
    function push(ch) {
        var s = { start: text.length, end: text.length + ch.length,
                  bold: st.b > 0, italic: st.i > 0, underline: st.u > 0,
                  link: st.a, color: st.color };
        var last = runs.length ? runs[runs.length - 1] : null;
        if (last && last.bold === s.bold && last.italic === s.italic &&
            last.underline === s.underline && last.link === s.link && last.color === s.color) {
            last.end = s.end;
        } else {
            runs.push(s);
        }
        text += ch;
    }
    while (i < n) {
        var c = html.charAt(i);
        if (c === "<") {
            var close = html.indexOf(">", i);
            if (close < 0) { push(html.substring(i)); break; }
            var tag = html.substring(i + 1, close).trim();
            var endTag = tag.charAt(0) === "/";
            var name = (endTag ? tag.substring(1) : tag).split(/[\s\/]/)[0].toLowerCase();
            if (name === "b" || name === "strong") st.b += endTag ? -1 : 1;
            else if (name === "i" || name === "em") st.i += endTag ? -1 : 1;
            else if (name === "u") st.u += endTag ? -1 : 1;
            else if (name === "a") {
                var m = /href\s*=\s*["']([^"']*)["']/i.exec(tag);
                st.a = endTag ? "" : (m ? m[1] : "");
            } else if (name === "font" || name === "span") {
                var cm = /color\s*[:=]\s*["']?\s*(#[0-9a-fA-F]{3,8}|[a-zA-Z]+)/.exec(tag);
                st.color = endTag ? "" : (cm ? cm[1] : st.color);
            } else if (name === "br") push(" ");
            else if (name === "img") {
                var am = /alt\s*=\s*["']([^"']*)["']/i.exec(tag);
                if (am && am[1].length) push("[" + am[1] + "]");
            }
            i = close + 1;
        } else if (c === "&") {
            var semi = html.indexOf(";", i);
            var ent = semi > 0 && semi - i <= 8 ? html.substring(i + 1, semi) : "";
            var map = { amp: "&", lt: "<", gt: ">", quot: "\"", apos: "'", nbsp: " " };
            if (ent in map) { push(map[ent]); i = semi + 1; }
            else if (ent.charAt(0) === "#") {
                var code = ent.charAt(1) === "x" ? parseInt(ent.substring(2), 16) : parseInt(ent.substring(1), 10);
                push(isNaN(code) ? "&" : String.fromCharCode(code)); i = semi + 1;
            } else { push("&"); i += 1; }
        } else { push(c); i += 1; }
    }
    return { text: text, runs: runs };
}
