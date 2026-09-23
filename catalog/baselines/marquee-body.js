// marquee-body.js — a notification body's markup, parsed to plain text + style runs,
// and the marquee's RING: the pure queue arithmetic behind the traversal invariant.
// Shipped beside the marquee's main.qml (which imports it by bare name) and run
// headless by scripts/check_marquee_body.py on synthetic inputs — the same code.
//
// ⚑ BODIES ARE MARKUP (W39). The freedesktop notification spec allows <b> <i>
// <u> <a href> <img src alt> in a BODY and says a server that does not support
// them "should filter them out"; Plasma's model passes its sanitised subset
// through, with <br> and entities. Un-stripped, the TAGS scrolled across the
// board as text. parseBody() returns the plain text plus STYLE RUNS — spans of
// bold / italic / underline / link / colour over the text — which the marquee
// reads as a fuller dot, a gated hue, an underline, a tappable href.
//
// ⚑ THE SUMMARY IS PLAIN (W45; operator, live: `notify-send 'oh <b>hi</b>'` put
// the markup in the SUMMARY and the stock popup showed it literally). The spec's
// markup is for the body only, so joinItem() pushes the app name and the summary
// as text and parses only the body.
.pragma library

// a text+runs accumulator: whitespace collapses at the push so run offsets are
// exact over the text the ring scrolls (they once drifted — s92 residue)
function _builder() {
    var b = { text: "", runs: [], st: { b: 0, i: 0, u: 0, a: "", color: "" } };
    b.push = function (ch) {
        ch = ch.replace(/\s+/g, " ");
        if (ch === " " && (b.text.length === 0 || b.text.charAt(b.text.length - 1) === " ")) return;
        var st = b.st;
        var s = { start: b.text.length, end: b.text.length + ch.length,
                  bold: st.b > 0, italic: st.i > 0, underline: st.u > 0,
                  link: st.a, color: st.color };
        var last = b.runs.length ? b.runs[b.runs.length - 1] : null;
        if (last && last.end === s.start && last.bold === s.bold && last.italic === s.italic &&
            last.underline === s.underline && last.link === s.link && last.color === s.color) {
            last.end = s.end;
        } else {
            b.runs.push(s);
        }
        b.text += ch;
    };
    // plain text: every character pushed as itself, no tag or entity read
    b.plain = function (s) {
        for (var k = 0; k < s.length; k++) b.push(s.charAt(k));
    };
    b.reset = function () { b.st = { b: 0, i: 0, u: 0, a: "", color: "" }; };
    b.result = function () {
        // a trailing space is dropped, and a run clamped to the kept length
        var text = b.text.replace(/\s+$/, ""), runs = [];
        for (var k = 0; k < b.runs.length; k++) {
            var r = b.runs[k], end = Math.min(r.end, text.length);
            if (end > r.start) runs.push({ start: r.start, end: end, bold: r.bold, italic: r.italic,
                                           underline: r.underline, link: r.link, color: r.color });
        }
        return { text: text, runs: runs };
    };
    return b;
}

function _parseInto(b, html) {
    var st = b.st, push = b.push;
    var i = 0, n = html.length;
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
}

function parseBody(html) {
    var b = _builder();
    _parseInto(b, html || "");
    // parseBody keeps a trailing space (the harness pins 'one<br>two' -> 'one two'
    // and a body ending in a space is the caller's to trim), so return the raw
    // accumulator, not result()
    return { text: b.text, runs: b.runs };
}

// one notification as the ring shows it: "app: summary — body", the first two
// PLAIN, the body parsed; runs are exact over the returned text
function joinItem(app, summary, body) {
    var b = _builder();
    if (app) b.plain(app + ": ");
    if (summary) b.plain(summary);
    if (body) {
        if (summary) b.plain(" — ");
        b.reset();
        _parseInto(b, body);
    }
    return b.result();
}

// ⚑ THE TRAVERSAL INVARIANT (W45; operator: "a notification should never be
// removed from the marquee while it's visible; it should always be allowed to
// scroll from offscreen to onscreen to offscreen at least once. Never 'just
// appear' and never vanish and never tear"). The QUEUE is every notification
// the marquee owes a rotation to, keyed by id, each with `shown` — has it had
// its rotation. The model only ever UPSERTS into the queue (arrivals, replaces);
// the queue only ever changes the ring at a rotation BOUNDARY, through ringNext.

// a queue entry: id, text, runs, shown — and, since W46, urgency (the model's
// 0 low / 1 normal / 2 critical; the board paints critical in the HOT token with
// heavy underlined dots and low with light dots — W72: never by colour alone) and transient (exactly one traversal, never re-queued)
// the placeholder a series run occupies in the joined text (U+2591, light shade —
// never a glyph in the registry; the painter skips it and draws columns instead)
var SERIES_CHAR = "░";

function queueItem(item, shown, history) {
    return { id: item.id, text: item.text, runs: item.runs, shown: shown,
             urgency: (item.urgency === undefined || item.urgency === null) ? 1 : item.urgency,
             transient: !!item.transient,
             // W46 actions: [{id, label}] as the model's ActionNames / ActionLabels roles
             actions: item.actions || [],
             // W46 jobs (the GAUGE, W48 folded): a job item's percentage HISTORY —
             // every distinct percentage seen, oldest first — and its state
             // (0 stopped / 1 running / 2 suspended); null percentage = not a job
             history: history || [], jobState: item.jobState === undefined ? null : item.jobState };
}

// a job's history grows by its new percentage when it differs from the last
function historyAfter(prev, item) {
    var h = prev ? prev.slice() : [];
    if (item.percentage === undefined || item.percentage === null) return h;
    if (!h.length || h[h.length - 1] !== item.percentage) h.push(item.percentage);
    return h;
}

// a replace (same id) takes the new text and owes a fresh rotation; a job's
// PROGRESS replace (same text, new percentage) keeps the item's place and its
// `shown` — a gauge ticking is not a new message, it is the same one moving
function queueUpsert(queue, item) {
    var out = [], found = false;
    for (var k = 0; k < queue.length; k++) {
        if (queue[k].id === item.id) {
            var h = historyAfter(queue[k].history, item);
            var progressOnly = queue[k].text === item.text && item.percentage !== undefined && item.percentage !== null;
            out.push(queueItem(item, progressOnly ? queue[k].shown : false, h));
            found = true;
        } else out.push(queue[k]);
    }
    if (!found) out.push(queueItem(item, false, historyAfter(null, item)));
    return out;
}

// at a boundary: the next ring is every UNSHOWN item (live or already gone —
// it was promised a rotation), then the items still live that have had theirs
// (they keep cycling), capped at maxItems. The new queue is the ring's live
// members marked shown plus whatever the cap held back, unchanged; an item
// gone from the model drops exactly after its rotation, never before.
function ringNext(queue, liveIds, maxItems) {
    var live = {};
    for (var k = 0; k < liveIds.length; k++) live[liveIds[k]] = true;
    var unshown = [], cycling = [];
    for (k = 0; k < queue.length; k++) {
        var q = queue[k];
        if (!q.shown) unshown.push(q);
        else if (live[q.id] && !q.transient) cycling.push(q);
        // shown and gone: dropped here; shown and TRANSIENT: one traversal was
        // the promise (W46), dropped even while live
    }
    var ring = unshown.concat(cycling), held = [];
    if (maxItems > 0 && ring.length > maxItems) {
        held = ring.slice(maxItems);
        ring = ring.slice(0, maxItems);
    }
    var next = [];
    for (k = 0; k < ring.length; k++)
        if (live[ring[k].id] && !ring[k].transient) next.push(queueItem(ring[k], true, ring[k].history));
    // held items keep their place and their `shown` — an unshown one is still owed
    for (k = 0; k < held.length; k++)
        if (!held[k].shown || live[held[k].id]) next.push(held[k]);
    return { ring: ring, queue: next };
}

// the ring's items as one scrolling text with the runs re-based, and each
// item's span with its urgency (W46: the painter reads it per character).
// ⚑ ACTIONS ARE RUNS (W46; catalog/notify-capabilities.md): each of an item's
// actions is appended after its text as " [Label]", a run carrying the action's
// id and the item's id — drawn like a link (the descent row lit) and, on a tap,
// handed to the model's invokeAction. The board becomes interactive with no new
// primitive: a run is what a tap already resolves to.
function ringJoin(items, sep) {
    var text = "", runs = [], spans = [];
    for (var k = 0; k < items.length; k++) {
        var it = items[k];
        if (!it.text.length) continue;
        if (text.length) text += sep;
        var base = text.length;
        for (var r = 0; r < it.runs.length; r++) {
            var run = it.runs[r];
            runs.push({ start: base + run.start, end: base + run.end, bold: run.bold,
                        italic: run.italic, underline: run.underline, link: run.link, color: run.color });
        }
        text += it.text;
        var acts = it.actions || [];
        for (var a = 0; a < acts.length; a++) {
            var label = " [" + acts[a].label + "]";
            runs.push({ start: text.length + 1, end: text.length + label.length, bold: false, italic: false,
                        underline: true, link: "", color: null, action: acts[a].id, item: it.id });
            text += label;
        }
        // ⚑ A JOB IS A GAUGE (W46; W48 folded): its percentage history becomes a
        // SERIES run after its text — one matrix COLUMN per sample, the newest at
        // the right, painted by seriesToColumns. The run reserves placeholder
        // characters (SERIES_CHAR, never a glyph) so indices stay consistent for
        // taps and spans: ceil(samples / cellsPerChar) of them.
        if (it.history && it.history.length) {
            var cpc = 6, n = it.history.length, chars = Math.ceil(n / cpc);
            var pad = " ";
            text += pad;
            runs.push({ start: text.length, end: text.length + chars, bold: false, italic: false, underline: false,
                        link: "", color: null, series: it.history.slice(), min: 0, max: 100, cellsPerChar: cpc,
                        item: it.id, jobState: it.jobState });
            for (var c = 0; c < chars; c++) text += SERIES_CHAR;
        }
        spans.push({ start: base, end: text.length, id: it.id,
                     urgency: (it.urgency === undefined || it.urgency === null) ? 1 : it.urgency });
    }
    return { text: text, runs: runs, spans: spans };
}

// ⚑ A SPARKLINE (W48, folded into W54's field): a series of values becomes
// COLUMN HEIGHTS on the matrix — one column per sample, oldest first, the newest
// at the right — the one thing a segment display cannot do and a matrix can. The
// height is round((v - min) / (max - min) * rows), clamped to [0, rows]; an empty
// series is no columns; a flat series (max == min) is a baseline of height 1 (a
// present signal with no range reads as a line, not as nothing); a value out of
// range clamps. Pure, so the board's painter lights rows [rows - h, rows) of each
// column and nothing else decides a height. Returned as an array of heights.
function seriesToColumns(values, rows, min, max) {
    var out = [];
    if (!values || !values.length || rows <= 0) return out;
    var flat = !(max > min);
    for (var i = 0; i < values.length; i++) {
        var v = values[i];
        if (typeof v !== "number" || isNaN(v)) { out.push(0); continue; }
        var h = flat ? 1 : Math.round((v - min) / (max - min) * rows);
        out.push(Math.max(0, Math.min(rows, h)));
    }
    return out;
}
