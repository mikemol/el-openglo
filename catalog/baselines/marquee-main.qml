import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
// the ACTIVE colour scheme's roles (⊕ONE-THEME, W35)
import org.kde.kirigami as Kirigami
// PUBLIC notification model (libnotificationmanager) — the same feed the stock
// applet reads. NOT the deprecated org.kde.plasma.private.notifications.
import org.kde.notificationmanager as NotificationManager
// the body-markup parser, shipped beside this file (W39)
import "marquee-body.js" as Body

PlasmoidItem {
    id: root
    // ⚑ BOUND, NOT BAKED (catalog/one-theme.md): lit = ForegroundNormal (the fg
    // token), ghost = ForegroundInactive (fg_in), void = [Colors:View]
    // BackgroundNormal (view) — read from the active scheme under the View set.
    // ONE package: applying EL-Amber.colors is what makes this board amber.
    Kirigami.Theme.colorSet: Kirigami.Theme.View
    Kirigami.Theme.inherit: false
    property color litColor: Kirigami.Theme.textColor
    property color ghostColor: Kirigami.Theme.disabledTextColor
    property color voidColor: Kirigami.Theme.backgroundColor
    // the HOT token (fg_act, ForegroundActive under View): a CRITICAL notification's
    // ink (W46; catalog/notify-capabilities.md) — attention's colour is the lit
    // token (the hover ring), alarm's is this one
    property color hotColor: Kirigami.Theme.activeTextColor
    // the unlit dot field's opacity — the palette's solved ghost_alpha, GLOBAL
    // across the variants (W23) and so bakeable in one package; passed to every
    // MatrixChar below in place of the component's authored 0.28. Whether a DOT
    // FIELD at this alpha reads as the same texture as strokes do is
    // ⊕GHOST-DENSITY's question, still open; the relation itself is one.
    property real ghostAlpha: 0.566

    // ⚑ THE SETTINGS (W34 c). Each reads plasmoid.configuration with the solved or
    // authored value as the fallback, so an unconfigured widget draws exactly
    // what the palette emitted; a slider is an override, never the source.
    property real cfgSpeed: (plasmoid.configuration.speed === undefined) ? 1.0
                            : plasmoid.configuration.speed
    property real cfgPitchScale: (plasmoid.configuration.pitchScale === undefined) ? 1.0
                                 : plasmoid.configuration.pitchScale
    property real cfgDotFill: (plasmoid.configuration.dotFill === undefined) ? 0.82
                              : plasmoid.configuration.dotFill
    property real cfgGhostAlpha: (plasmoid.configuration.ghostAlpha === undefined) ? root.ghostAlpha
                                 : plasmoid.configuration.ghostAlpha
    property bool cfgShowField: (plasmoid.configuration.showField === undefined) ? true
                                : plasmoid.configuration.showField
    property string cfgIdleText: (plasmoid.configuration.idleText === undefined) ? ""
                                 : plasmoid.configuration.idleText
    property int cfgMaxItems: (plasmoid.configuration.maxItems === undefined) ? 12
                              : plasmoid.configuration.maxItems
    property bool cfgOpenLinks: (plasmoid.configuration.openLinks === undefined) ? true
                                : plasmoid.configuration.openLinks
    property bool cfgHoverPause: (plasmoid.configuration.hoverPause === undefined) ? true
                                 : plasmoid.configuration.hoverPause
    // ⚑ THE LIVE HOST'S TRACE (operator, 2026-09-22: a single notify-send after a
    // plasmashell replace showed nothing; under `watch` things eventually
    // appeared — and the headless run passes). What check_marquee_live samples
    // under the stub, this prints under the real model: every rebuild, swap and
    // start, on plasmashell's stderr, when the setting is on.
    property bool cfgDebugLog: (plasmoid.configuration.debugLog === undefined) ? false
                               : plasmoid.configuration.debugLog
    // ⚑ AND INTO THE APPLET'S CONFIG (operator: "check the logs yourself on
    // ticks"). A plasmashell started from a terminal logs to that terminal,
    // which nothing else can read; plasmoid.configuration is persisted to the
    // appletsrc on disk, which scripts/check_marquee_host.py reads. The last
    // ~6000 characters are kept, newest last, each line stamped in seconds
    // since the widget loaded.
    readonly property double loadedAt: Date.now()
    function trace(what) {
        if (!root.cfgDebugLog) return;
        console.log("el-marquee " + what);
        var line = ((Date.now() - root.loadedAt) / 1000).toFixed(2) + " " + what;
        var log = (plasmoid.configuration.traceLog || "") + line + "\n";
        if (log.length > 6000) log = log.substring(log.length - 6000);
        plasmoid.configuration.traceLog = log;
    }

    preferredRepresentation: fullRepresentation

    // --- the notification feed (degrades to idle if unavailable) ------------
    //
    // ⚑ A DOUBLE-BUFFERED RING (W38; operator, live 2026-09-22: "they blip in
    // and out in accompaniment with the notification dialogs"). rebuild() used
    // to replace the scrolling text on every count change, so the Row was torn
    // down mid-scroll whenever a popup appeared or expired. Now the model
    // writes PENDING only; ACTIVE is what scrolls and it is replaced by pending
    // at the animation's loop boundary — a full rotation — never mid-word. A
    // notification that expired leaves at the boundary too; an empty pending
    // drains the ring to the idle field at the boundary.
    property string tickerText: ""        // ACTIVE: what is scrolling now
    property bool haveModel: false

    // ⚑ THE TRAVERSAL INVARIANT (W45; operator: "never 'just appear' and never
    // vanish and never tear"). root.queue is every notification the board owes
    // a rotation to, keyed by the model's notificationId; rebuild() only UPSERTS
    // into it, and swapRing() — at the rotation boundary, nowhere else — asks
    // Body.ringNext for the next ring: every unshown item (expired or not)
    // scrolls once, a live item keeps cycling, an item gone from the model drops
    // only after its rotation. The arithmetic is pure and run headless by
    // check_marquee_body's ring scenarios.
    property var queue: []
    // ⚑ OBSERVABLE FROM OUTSIDE (W49). The Row and its animation live inside
    // fullRepresentation, which no harness can reach by id; the board reports
    // its x and whether a rotation is running here so check_marquee_live can
    // sample them per frame under the stubbed model.
    property real boardX: 0
    property real boardRawX: 0
    property real boardWidth: 0
    property bool boardRunning: false
    // W51: the hover-pause is holding the board, and the ring's current opacity
    property bool boardPaused: false
    property real ringOpacity: 0
    // W46: the distinct ink colours the last backdrop paint used (a critical item
    // puts the hot token here) and the text that paint drew — what
    // check_marquee_live's L9 reads. The paint follows the swap by a turn (the
    // backdrop's resize commits on a paint cycle), so ink is judged against
    // paintedText, never against tickerText.
    property var paintedInk: []
    property string paintedText: ""
    // ...and the column heights of every series (gauge) that paint drew (L11)
    property var paintedSeries: []

    function liveIds() {
        var ids = [];
        for (var i = 0; i < notifModel.count; i++)
            ids.push(notifModel.data(notifModel.index(i, 0), NotificationManager.Notifications.IdRole));
        return ids;
    }

    function swapRing() {
        var live = root.liveIds();
        var next = Body.ringNext(root.queue, live, root.cfgMaxItems);
        root.queue = next.queue;
        var joined = Body.ringJoin(next.ring, "     •     ");
        root.trace("swap live=" + JSON.stringify(live) + " ring=" + JSON.stringify(next.ring.map(function (i) { return i.id; }))
                   + " queue=" + JSON.stringify(next.queue.map(function (i) { return [i.id, i.shown]; }))
                   + " text=" + JSON.stringify(joined.text));
        root.tickerText = joined.text;         // empty -> the ring drains to idle
        root.tickerRuns = joined.runs;
        root.tickerSpans = joined.spans;       // each item's span with its urgency (W46)
        // ⚑ THE PAINT FOLLOWS THE SWAP, NOT THE TEXT (measured s129: a job's three
        // progress replaces grew its history, every swap re-rang it, and the
        // gauge never repainted — the joined text was identical each time, so a
        // paint keyed on tickerTextChanged had nothing to fire on).
        root.ringSwapped();
    }
    signal ringSwapped()
    property var tickerSpans: []
    // the urgency of the item character i belongs to: 0 low, 1 normal, 2 critical
    function urgencyAt(i) {
        var ss = root.tickerSpans;
        for (var k = 0; k < ss.length; k++)
            if (i >= ss[k].start && i < ss[k].end) return ss[k].urgency;
        return 1;
    }

    // ⚑ BODIES ARE MARKUP (W39). The spec allows <b> <i> <u> <a> <img>; Plasma
    // passes its sanitised subset through with <br> and entities; un-stripped,
    // the TAGS scrolled across the board as text. Body.parseBody (marquee-body.js,
    // shipped beside this file and run headless by check_marquee_body) returns
    // the plain text plus STYLE RUNS (bold / italic / underline / link / colour
    // spans), read below as a fuller dot, a gated hue, an underline, a href.
    property var tickerRuns: []

    // ⚑ THE SOLVED HUE TABLES (relations.md §5a; make_palette.hue_table, gated by
    // check_rehue). Twelve buckets per variant, index = hue / 30; a bucket the
    // gate refused already holds the lit token, so a lookup can never produce an
    // unreadable colour. ONE package carries every variant's table keyed by that
    // variant's fg hex, and the row is picked from the LIVE lit colour — the one
    // per-variant fact that is not a scheme role (catalog/one-theme.md). A
    // foreign scheme (a fg matching no variant) gets the fallback row, whose
    // buckets fall back to fg anyway. No colour arithmetic beyond the lookup.
    readonly property var hueTables: ({"#99ffeb": ["#ff9999", "#ffcc99", "#ffff99", "#ccff99", "#99ff99", "#99ffcc", "#99ffff", "#99ffeb", "#99ffeb", "#99ffeb", "#ff99ff", "#99ffeb"], "#002921": ["#290000", "#291400", "#292900", "#142900", "#002900", "#002914", "#002929", "#001429", "#000029", "#140029", "#290029", "#290014"], "#99ccff": ["#ff9999", "#ffcc99", "#ffff99", "#ccff99", "#99ff99", "#99ffcc", "#99ffff", "#99ccff", "#99ccff", "#99ccff", "#99ccff", "#ff99cc"], "#001429": ["#290000", "#291400", "#292900", "#142900", "#002900", "#002914", "#002929", "#001429", "#000029", "#140029", "#290029", "#290014"], "#ffd499": ["#ffd499", "#ffd499", "#ffff99", "#ccff99", "#99ff99", "#99ffcc", "#99ffff", "#99ccff", "#ffd499", "#ffd499", "#ff99ff", "#ff99cc"], "#291800": ["#290000", "#291400", "#292900", "#142900", "#002900", "#002914", "#002929", "#001429", "#000029", "#140029", "#290029", "#290014"]})
    readonly property string fallbackFg: "#99ffeb"
    readonly property var hueTable: (String(root.litColor) in hueTables) ? hueTables[String(root.litColor)]
                                                                        : hueTables[fallbackFg]
    // bold is a fuller dot: the clock's weight ratio, on the dot's area
    readonly property real boldFill: 1.15

    function runAt(i) {
        var rs = root.tickerRuns;
        for (var k = 0; k < rs.length; k++)
            if (i >= rs[k].start && i < rs[k].end) return rs[k];
        return null;
    }
    // ⚑ A TAP RESOLVES TO A RUN (W40 links; W46 actions). The pointer's board x
    // against the text's left edge and the character advance gives a character
    // index; a link run opens externally, an ACTION run calls the model's
    // invokeAction on the row that still carries the item (found by id — the
    // ring may lag the model). Exposed as a function so the harness can tap
    // without synthesising a pointer; returns what it did, for the trace.
    property real charAdvance: 0        // set by the representation: one cell advance in px
    property var lastTap: null
    function tapAt(x) {
        if (root.charAdvance <= 0) return null;
        var idx = Math.floor((x - root.boardRawX) / root.charAdvance);
        var run = root.runAt(idx);
        var did = { index: idx, kind: "none" };
        if (run && run.action !== undefined && run.action !== null) {
            var row = -1;
            for (var i = 0; i < notifModel.count; i++)
                if (notifModel.data(notifModel.index(i, 0), NotificationManager.Notifications.IdRole) === run.item) { row = i; break; }
            did = { index: idx, kind: "action", action: run.action, item: run.item, row: row };
            if (row >= 0) notifModel.invokeAction(notifModel.index(row, 0), run.action);
        } else if (run && run.link.length > 0) {
            did = { index: idx, kind: "link", link: run.link };
            Qt.openUrlExternally(run.link);
        }
        root.trace("tap x=" + x.toFixed(1) + " -> " + JSON.stringify(did));
        root.lastTap = did;
        return did;
    }
    // a run's colour ("#rrggbb" or a CSS basic name) -> the table's colour, or
    // transparent (no override) when the colour is not recognised
    readonly property var cssNames: ({ red: 0, orange: 30, yellow: 60, lime: 90, green: 120,
                                       teal: 180, cyan: 180, aqua: 180, blue: 240, navy: 240,
                                       purple: 270, magenta: 300, fuchsia: 300, pink: 330 })
    function hueOf(c) {
        if (!c) return -1;
        var s = ("" + c).toLowerCase();
        if (s in cssNames) return cssNames[s];
        var m = /^#([0-9a-f]{6})$/.exec(s);
        if (!m) {
            var m3 = /^#([0-9a-f])([0-9a-f])([0-9a-f])$/.exec(s);
            if (!m3) return -1;
            s = "#" + m3[1] + m3[1] + m3[2] + m3[2] + m3[3] + m3[3];
            m = /^#([0-9a-f]{6})$/.exec(s);
        }
        var r = parseInt(m[1].substring(0, 2), 16) / 255, g = parseInt(m[1].substring(2, 4), 16) / 255,
            b = parseInt(m[1].substring(4, 6), 16) / 255;
        var mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
        if (d < 0.08) return -1;                 // grey: no hue to read
        var h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
        return ((h * 60) + 360) % 360;
    }
    function overrideFor(run) {
        if (!run || !run.color) return "transparent";
        var h = hueOf(run.color);
        if (h < 0) return "transparent";
        return root.hueTable[Math.round(h / 30) % root.hueTable.length];
    }

    NotificationManager.Notifications {
        id: notifModel
        showNotifications: true
        showJobs: true
        // newest first so the ticker leads with the latest
        sortMode: NotificationManager.Notifications.SortByDate
        groupMode: NotificationManager.Notifications.GroupDisabled
        Component.onCompleted: root.haveModel = true
        // ⚑ CAPTURE AT INSERTION (operator's trace, 2026-09-22: every single
        // notify-send logged `rebuild count=0` — the model had inserted the row
        // and removed it again before its countChanged reached us, so nothing was
        // ever read; only a second notification sent while one was live stayed
        // long enough). rowsInserted is delivered synchronously, with the rows
        // readable, before anything can remove them: an arrival is owed its
        // rotation whatever its lifetime, and this is where it is claimed.
        onRowsInserted: (parent, first, last) => root.capture(first, last)
        // ...and the second net (host trace read on a tick, 2026-09-22: a lone
        // notification's ONLY signal was a countChanged at its expiry, ~5 s
        // after notify-send). Removal is always signalled, and this is delivered
        // with the row still readable — whatever was never inserted in our sight
        // is claimed on its way out.
        onRowsAboutToBeRemoved: (parent, first, last) => root.capture(first, last)
        onCountChanged: root.rebuild()
        // a replace (same id, new text) changes no count; it changes data
        onDataChanged: root.rebuild()
    }

    function capture(first, last) {
        var q = root.queue;
        for (var i = first; i <= last; i++) q = root.upsertRow(q, i);
        root.queue = q;
        root.trace("capture rows " + first + "-" + last + " queue=" + q.length + " ticker=" + JSON.stringify(root.tickerText));
        if (root.tickerText.length === 0) root.swapRing();
    }

    // one model row into the queue: a new id is owed a rotation, a known id with
    // new text is owed one again, an unchanged id is left alone
    function upsertRow(q, i) {
        var idx = notifModel.index(i, 0);
        var id = notifModel.data(idx, NotificationManager.Notifications.IdRole);
        var app = notifModel.data(idx, NotificationManager.Notifications.ApplicationNameRole);
        var sum = notifModel.data(idx, NotificationManager.Notifications.SummaryRole);
        var body = notifModel.data(idx, NotificationManager.Notifications.BodyRole);
        // W46: urgency (0 low / 1 normal / 2 critical) and transient, as the model
        // declares them (check_notify_roles); undefined reads as normal, not transient
        var urg = notifModel.data(idx, NotificationManager.Notifications.UrgencyRole);
        var trans = notifModel.data(idx, NotificationManager.Notifications.TransientRole);
        // W46 actions: parallel lists of ids and labels, as the model declares them
        var names = notifModel.data(idx, NotificationManager.Notifications.ActionNamesRole) || [];
        var labels = notifModel.data(idx, NotificationManager.Notifications.ActionLabelsRole) || [];
        var actions = [];
        for (var a = 0; a < names.length; a++) actions.push({ id: names[a], label: labels[a] !== undefined ? labels[a] : names[a] });
        // W46 jobs (the gauge): a Job-type row brings its percentage and state; the
        // queue keeps the percentage history (Body.queueUpsert)
        var type = notifModel.data(idx, NotificationManager.Notifications.TypeRole);
        var isJob = type === NotificationManager.Notifications.JobType;
        var pct = isJob ? notifModel.data(idx, NotificationManager.Notifications.PercentageRole) : null;
        var jobState = isJob ? notifModel.data(idx, NotificationManager.Notifications.JobStateRole) : null;
        // the summary is PLAIN, the body is markup (W45): Body.joinItem
        var item = Body.joinItem(app, sum, body);
        if (!item.text.length || id === undefined) return q;
        for (var k = 0; k < q.length; k++)
            if (q[k].id === id && q[k].text === item.text) {
                // an unchanged item is left alone — unless it is a job whose percentage moved
                var hist = q[k].history || [];
                if (!isJob || pct === null || pct === undefined || (hist.length && hist[hist.length - 1] === pct)) return q;
            }
        root.trace("upsert id=" + JSON.stringify(id) + " text=" + JSON.stringify(item.text)
                   + " urgency=" + JSON.stringify(urg) + " transient=" + JSON.stringify(trans)
                   + " actions=" + JSON.stringify(actions.map(function (x) { return x.id; }))
                   + (isJob ? " job pct=" + JSON.stringify(pct) + " state=" + JSON.stringify(jobState) : ""));
        return Body.queueUpsert(q, { id: id, text: item.text, runs: item.runs, urgency: urg, transient: trans === true,
                                     actions: actions, percentage: isJob ? pct : null, jobState: jobState });
    }

    // the model changed: upsert every live notification into the queue. A new id
    // is owed a rotation; a known id with new text (a replace) is owed one again;
    // an unchanged id is left as it stands. The ring is NOT touched here.
    function rebuild() {
        var q = root.queue;
        for (var i = 0; i < notifModel.count; i++) q = root.upsertRow(q, i);
        root.queue = q;
        root.trace("rebuild count=" + notifModel.count + " queue=" + q.length + " ticker=" + JSON.stringify(root.tickerText));
        // nothing is scrolling: start this rotation now rather than at a boundary
        // that will never come
        if (root.tickerText.length === 0) root.swapRing();
    }

    // ⚑ THE DISPLAY REGISTRY, EMITTED — NOT RETYPED.  display_types.as_qml_js()
    // is the single source; this surface holds no font and no geometry of its own.
    // It rendered `font.family: "monospace"` before, which is why
    // check_geometry_source flagged it: a phosphor ticker drawn in the system's
    // font is not this theme, it is text that happens to be the right colour.
    // 5x8: the body rows plus one descent row, so lowercase notification text
    // keeps its descenders. The table is the authored FONT5x8 plus the Latin-1
    // extension rasterised at build time (⊕MATRIX-FONT-INPUT).
    property var registry: {"displays": {"5x8": {"baseline": 6, "cell": [5.0, 8.0], "cols": 5, "font": "5x8", "kind": "matrix", "rows": 8}}, "font5x8": {" ": [0, 0, 0, 0, 0], "!": [79, 95, 95, 95, 95], "\"": [3, 3, 0, 3, 3], "#": [20, 30, 20, 28, 20], "$": [38, 69, 127, 73, 50], "%": [7, 37, 24, 66, 112], "&": [112, 79, 85, 99, 64], "'": [1, 7, 7, 7, 1], "(": [60, 126, 131, 129, 0], ")": [0, 129, 131, 126, 124], "*": [20, 8, 62, 8, 20], "+": [8, 8, 62, 8, 8], ",": [0, 192, 96, 96, 0], "-": [8, 8, 8, 8, 8], ".": [0, 96, 96, 0, 0], "/": [32, 16, 8, 4, 2], "0": [62, 81, 73, 69, 62], "1": [0, 66, 127, 64, 0], "2": [66, 97, 81, 73, 70], "3": [33, 65, 69, 75, 49], "4": [24, 20, 18, 127, 16], "5": [39, 69, 69, 69, 57], "6": [60, 74, 73, 73, 48], "7": [1, 113, 9, 5, 3], "8": [54, 73, 73, 73, 54], "9": [6, 73, 73, 41, 30], ":": [0, 54, 54, 0, 0], ";": [0, 192, 102, 102, 0], "<": [8, 20, 20, 34, 34], "=": [20, 20, 20, 20, 20], ">": [34, 34, 20, 20, 8], "?": [2, 1, 81, 9, 6], "@": [126, 61, 2, 60, 63], "A": [126, 9, 9, 9, 126], "B": [127, 73, 73, 73, 54], "C": [62, 65, 65, 65, 34], "D": [127, 65, 65, 34, 28], "E": [127, 73, 73, 73, 65], "F": [127, 9, 9, 9, 1], "G": [62, 65, 73, 73, 122], "H": [127, 8, 8, 8, 127], "I": [0, 65, 127, 65, 0], "J": [32, 64, 65, 63, 1], "K": [127, 8, 20, 34, 65], "L": [127, 64, 64, 64, 64], "M": [127, 2, 12, 2, 127], "N": [127, 4, 8, 16, 127], "O": [62, 65, 65, 65, 62], "P": [127, 9, 9, 9, 6], "Q": [62, 65, 81, 33, 94], "R": [127, 9, 25, 41, 70], "S": [70, 73, 73, 73, 49], "T": [1, 1, 127, 1, 1], "U": [63, 64, 64, 64, 63], "V": [31, 32, 64, 32, 31], "W": [127, 32, 24, 32, 127], "X": [99, 20, 8, 20, 99], "Y": [3, 4, 120, 4, 3], "Z": [97, 81, 73, 69, 67], "[": [255, 255, 0, 0, 0], "\\": [0, 3, 12, 48, 64], "]": [0, 0, 0, 255, 255], "^": [24, 6, 1, 6, 24], "`": [0, 0, 0, 1, 0], "a": [32, 84, 84, 84, 120], "b": [127, 68, 68, 68, 56], "c": [56, 68, 68, 68, 68], "d": [56, 68, 68, 68, 127], "e": [56, 84, 84, 84, 88], "f": [8, 126, 9, 1, 2], "g": [24, 164, 164, 164, 124], "h": [127, 4, 4, 4, 120], "i": [0, 68, 125, 64, 0], "j": [64, 128, 132, 125, 0], "k": [127, 16, 40, 68, 0], "l": [0, 65, 127, 64, 0], "m": [124, 4, 24, 4, 120], "n": [124, 4, 4, 4, 120], "o": [56, 68, 68, 68, 56], "p": [252, 36, 36, 36, 24], "q": [24, 36, 36, 36, 252], "r": [124, 8, 4, 4, 8], "s": [72, 84, 84, 84, 36], "t": [4, 63, 68, 64, 32], "u": [60, 64, 64, 32, 124], "v": [28, 32, 64, 32, 28], "w": [60, 64, 48, 64, 60], "x": [68, 40, 16, 40, 68], "y": [28, 160, 160, 160, 124], "z": [68, 100, 84, 76, 68], "{": [16, 24, 239, 0, 0], "|": [255, 255, 255, 255, 255], "}": [0, 0, 239, 24, 16], "~": [8, 8, 8, 8, 8], "\u00a1": [246, 254, 254, 254, 246], "\u00a2": [28, 34, 127, 34, 48], "\u00a3": [72, 127, 73, 65, 64], "\u00a4": [62, 50, 34, 50, 62], "\u00a5": [1, 46, 120, 46, 1], "\u00a6": [239, 239, 239, 239, 239], "\u00a7": [73, 22, 148, 52, 109], "\u00a8": [1, 0, 0, 0, 1], "\u00a9": [12, 94, 66, 82, 12], "\u00aa": [5, 10, 2, 7, 8], "\u00ab": [24, 44, 0, 56, 4], "\u00ac": [8, 8, 8, 8, 56], "\u00ad": [16, 16, 16, 16, 16], "\u00ae": [12, 94, 74, 86, 12], "\u00b0": [2, 5, 5, 5, 2], "\u00b1": [72, 72, 94, 72, 72], "\u00b2": [9, 13, 12, 11, 11], "\u00b3": [9, 8, 10, 11, 13], "\u00b4": [0, 1, 0, 0, 0], "\u00b5": [254, 64, 64, 64, 126], "\u00b6": [6, 15, 127, 1, 1], "\u00b7": [24, 24, 24, 24, 24], "\u00b8": [0, 128, 128, 128, 128], "\u00b9": [9, 9, 15, 8, 8], "\u00ba": [7, 0, 8, 0, 7], "\u00bb": [4, 56, 0, 44, 24], "\u00bc": [9, 40, 8, 1, 120], "\u00bd": [9, 40, 8, 106, 88], "\u00be": [9, 79, 32, 2, 120], "\u00bf": [96, 16, 152, 0, 64], "\u00c0": [96, 28, 19, 28, 96], "\u00c1": [96, 28, 19, 28, 96], "\u00c2": [96, 28, 19, 28, 96], "\u00c3": [96, 28, 19, 28, 96], "\u00c4": [96, 28, 19, 28, 96], "\u00c5": [96, 28, 19, 28, 96], "\u00c6": [96, 28, 19, 127, 73], "\u00c7": [62, 65, 193, 65, 34], "\u00c8": [127, 73, 73, 73, 65], "\u00c9": [127, 73, 73, 73, 65], "\u00ca": [127, 73, 73, 73, 65], "\u00cb": [127, 73, 73, 73, 65], "\u00cc": [65, 65, 127, 65, 65], "\u00cd": [65, 65, 127, 65, 65], "\u00ce": [65, 65, 127, 65, 65], "\u00cf": [65, 65, 127, 65, 65], "\u00d0": [127, 127, 73, 65, 62], "\u00d1": [127, 7, 28, 112, 127], "\u00d2": [62, 65, 65, 65, 62], "\u00d3": [62, 65, 65, 65, 62], "\u00d4": [62, 65, 65, 65, 62], "\u00d5": [62, 65, 65, 65, 62], "\u00d6": [62, 65, 65, 65, 62], "\u00d7": [34, 20, 8, 20, 34], "\u00d8": [94, 113, 73, 71, 63], "\u00d9": [63, 64, 64, 64, 63], "\u00da": [63, 64, 64, 64, 63], "\u00db": [63, 64, 64, 64, 63], "\u00dc": [63, 64, 64, 64, 63], "\u00dd": [1, 6, 120, 6, 1], "\u00de": [127, 34, 34, 18, 28], "\u00df": [127, 0, 64, 75, 112], "\u00e0": [116, 66, 74, 124, 64], "\u00e1": [116, 66, 75, 124, 64], "\u00e2": [116, 67, 74, 124, 64], "\u00e3": [116, 66, 75, 125, 64], "\u00e4": [116, 67, 74, 124, 64], "\u00e5": [116, 67, 75, 124, 64], "\u00e6": [116, 74, 124, 82, 92], "\u00e7": [60, 70, 194, 66, 36], "\u00e8": [60, 82, 83, 82, 28], "\u00e9": [60, 82, 83, 82, 28], "\u00ea": [60, 82, 82, 83, 28], "\u00eb": [60, 83, 82, 83, 28], "\u00ec": [64, 66, 127, 64, 64], "\u00ed": [64, 66, 127, 64, 64], "\u00ee": [64, 67, 126, 64, 64], "\u00ef": [64, 67, 126, 65, 64], "\u00f0": [56, 69, 69, 71, 60], "\u00f1": [126, 4, 3, 3, 124], "\u00f2": [60, 66, 67, 66, 60], "\u00f3": [60, 66, 67, 66, 60], "\u00f4": [60, 67, 66, 67, 60], "\u00f5": [60, 66, 67, 67, 60], "\u00f6": [60, 67, 66, 67, 60], "\u00f7": [8, 8, 42, 8, 8], "\u00f8": [124, 98, 82, 70, 60], "\u00f9": [126, 64, 65, 64, 126], "\u00fa": [126, 64, 65, 64, 126], "\u00fb": [126, 65, 64, 65, 126], "\u00fc": [126, 65, 64, 65, 126], "\u00fd": [4, 24, 97, 24, 4], "\u00fe": [255, 68, 66, 66, 60], "\u00ff": [4, 25, 96, 25, 4]}, "fontExtension": {"glyphs": 118, "path": "LiberationMono-Regular.ttf"}, "lattice": ["7", "9", "14", "16", "5x7", "5x8"]}
    property var matrix: registry.displays["5x8"]
    property var matrixFont: registry["font" + matrix.font]

    fullRepresentation: Item {
        id: rep
        Layout.minimumWidth: 200
        Layout.preferredWidth: 420
        clip: true

        // dot pitch from the panel height: the cell is `rows` dots tall, and we
        // leave a little vertical air so the glyph does not touch the bezel.
        property real pitch: Math.max(1, (height * 0.72) / root.matrix.rows * root.cfgPitchScale)
        property real cellW: root.matrix.cols * pitch
        property real advance: cellW + pitch      // one blank column between chars

        Rectangle { anchors.fill: parent; color: root.voidColor; radius: height*0.1 }

        // ⚑ THE FIELD IS THE HARDWARE, AND IT IS AN APERTURE (W54; relations.md
        // §5b). Every LED, bezel to bezel, drawn once and never moved; each is a
        // pinhole over a BACKDROP drawn at `scale` backdrop pixels per pitch, and
        // its brightness is the ink under its aperture at the current offset —
        // graded, never snapped. The text is painted into the backdrop from the
        // registry's column bytes (one cell per dot, so 1:1 with the pips by
        // construction) and the scroll is the field's `offset`: a number, no Row
        // rebuilt, no x quantised to the pitch. Measured (s118, check_marquee_live
        // --motion): the snapped Row moved in 3.6 px quanta at velocity cv 0.104
        // — the jump the operator saw live; the field grades at cv 0.02.
        ApertureField {
            id: field
            anchors.fill: parent
            showGhost: root.cfgShowField
            rows: root.matrix.rows
            u: rep.pitch
            scale: 4
            dotFill: root.cfgDotFill
            ghostColor: root.ghostColor
            ghostOpacity: root.cfgGhostAlpha
            litColor: root.litColor
            colourFromInk: true
            // ⚑ THE HOVER-PAUSE SHOWS ITSELF (W51). While the pause holds the board,
            // the outermost pips breathe from the ghost's weight up toward lit and
            // back — the LIT token, not the hot one: this is attention, not alarm
            // (urgency owns fg_act, W46). The moment the pointer leaves, the run
            // resumes and the ring goes dark. The ring is drawn regardless of
            // cfgShowField.
            ringColor: root.litColor
            onRingOpacityChanged: root.ringOpacity = ringOpacity
            SequentialAnimation on ringOpacity {
                id: pulse
                running: root.boardPaused
                loops: Animation.Infinite
                NumberAnimation { from: root.cfgGhostAlpha; to: 0.9; duration: 400; easing.type: Easing.InOutSine }
                NumberAnimation { from: 0.9; to: root.cfgGhostAlpha; duration: 400; easing.type: Easing.InOutSine }
                onRunningChanged: if (!running) field.ringOpacity = 0
            }
            onBackdropReady: rep.paintBackdrop()
            onBackdropSized: rep.drawBackdrop()
            onColsChanged: if (backdrop.available) rep.paintBackdrop()
            // the text's left edge on screen, in px: the observables the harness reads
            onOffsetChanged: { root.boardRawX = rep.width - (offset / scale) * rep.pitch; root.boardX = root.boardRawX; }
        }

        // one character advance, in backdrop cells: the glyph's columns plus a blank
        readonly property int advanceCells: root.matrix.cols + 1
        onPitchChanged: root.charAdvance = advanceCells * pitch
        // the scrolling text's width, in cells and in px
        readonly property int textCells: root.tickerText.length * advanceCells
        readonly property real textWidth: textCells * pitch

        // ⚑ THE BACKDROP: the ticker (or, idle, the settings' idle text centred on
        // the board) painted as CELLS from the registry's column bytes. A bold run
        // widens each dot by half a cell into its neighbours — a heavier weight the
        // aperture grades; a coloured run is painted in the solved table's colour
        // (never the sender's literal) and the field reads it back per pip; a link
        // or <u> run lights its descent row (W40).
        // paint = size the backdrop for the text, then draw once the field says the
        // buffer is real (ApertureField.sizeBackdrop / backdropSized)
        function paintBackdrop() {
            var idle = root.tickerText.length === 0;
            var text = idle ? root.cfgIdleText : root.tickerText;
            var cells = text.length * rep.advanceCells;
            field.sizeBackdrop((idle ? field.cols : field.cols + cells) * field.scale);
        }
        function drawBackdrop() {
            var s = field.scale, cols = field.cols;
            var idle = root.tickerText.length === 0;
            var text = idle ? root.cfgIdleText : root.tickerText;
            var cells = text.length * rep.advanceCells;
            var ctx = field.backdrop.getContext("2d");
            ctx.clearRect(0, 0, field.backdrop.width, field.backdrop.height);
            var x0 = idle ? Math.round((cols - cells) / 2) : cols;
            var onCells = 0, inks = {};
            var seriesDrawn = [];
            for (var i = 0; i < text.length; i++) {
                var ch = text.charAt(i);
                var run = idle ? null : root.runAt(i);
                // ⚑ THE GAUGE (W46; W48's painter, folded): a series run's characters are
                // placeholders; at its first one the run's history is painted as COLUMNS —
                // one matrix column per sample, rows [rows-h, rows) lit, the newest at the
                // right (seriesToColumns) — in the item's ink, half ink while suspended
                if (run && run.series) {
                    if (i === run.start) {
                        var heights = Body.seriesToColumns(run.series, root.matrix.rows, run.min, run.max);
                        var u0 = idle ? 1 : root.urgencyAt(i);
                        ctx.fillStyle = u0 === 2 ? String(root.hotColor) : String(root.litColor);
                        ctx.globalAlpha = (run.jobState === 2 || u0 === 0) ? 0.5 : 1.0;
                        inks[ctx.fillStyle] = true;
                        for (var sc = 0; sc < heights.length; sc++) {
                            for (var rr = root.matrix.rows - heights[sc]; rr < root.matrix.rows; rr++) {
                                ctx.fillRect((x0 + run.start * rep.advanceCells + sc) * s, rr * s, s, s);
                                onCells += 1;
                            }
                        }
                        seriesDrawn.push(heights);
                    }
                    continue;
                }
                var bytes = root.matrixFont[ch] || root.matrixFont[ch.toUpperCase()] || root.matrixFont["?"] || [];
                var colour = root.overrideFor(run);
                // W46 urgency: CRITICAL is painted in the hot token (over any run
                // colour — alarm outranks a sender's hue); LOW at half ink, which
                // the aperture reads as half coverage — weight is a number here
                var urgency = idle ? 1 : root.urgencyAt(i);
                ctx.fillStyle = urgency === 2 ? String(root.hotColor)
                              : (colour !== "transparent") ? colour : String(root.litColor);
                ctx.globalAlpha = urgency === 0 ? 0.5 : 1.0;
                inks[ctx.fillStyle] = true;
                var grow = (run && run.bold) ? s / 2 : 0;
                var underline = run !== null && (run.link.length > 0 || run.underline);
                for (var c = 0; c < root.matrix.cols; c++) {
                    var byte = bytes.length > c ? bytes[c] : 0;
                    for (var r = 0; r < root.matrix.rows; r++) {
                        var on = ((byte & (1 << r)) !== 0) || (underline && r === root.matrix.rows - 1);
                        if (!on) continue;
                        onCells += 1;
                        var cx = (x0 + i * rep.advanceCells + c) * s, cy = r * s;
                        ctx.fillRect(cx - grow, cy - grow, s + 2 * grow, s + 2 * grow);
                    }
                }
            }
            ctx.globalAlpha = 1.0;
            root.paintedInk = Object.keys(inks);
            root.paintedText = idle ? "" : text;
            root.paintedSeries = seriesDrawn;
            if (idle) field.offset = 0;              // the idle face sits still, centred
            field.sample();
            var ink = 0;                              // the backdrop's ink, in backdrop pixels
            for (var k = 0; k < field.prefix.length; k++) ink += field.prefix[k][field.backdropWidth];
            // onCells x scale^2 = ink when every cell landed: the resize rule above
            root.trace("paint idle=" + idle + " cells=" + cells + " backdrop=" + field.backdrop.width + "x" + field.backdrop.height
                       + " cols=" + cols + " onCells=" + onCells + " ink=" + ink.toFixed(0));
            root.boardWidth = idle ? 0 : cells * rep.pitch;
        }

        // the ring swapped (text, runs, spans or a gauge's history): repaint the
        // backdrop and start its run
        Connections {
            target: root
            function onRingSwapped() { if (field.backdrop.available) rep.paintBackdrop(); Qt.callLater(rep.startRun); }
            function onCfgIdleTextChanged() { if (field.backdrop.available) rep.paintBackdrop(); }
        }

        // ⚑ THE ROTATION IS STARTED, NEVER BOUND (operator, live 2026-09-22:
        // "doesn't respond to notifications at all"): a `running:` binding is
        // overwritten by a finite animation's own completion. The endpoints are
        // SET when the run starts: from 0 (the text just off the right edge of the
        // backdrop's board-width margin) to the board plus the text, in backdrop
        // pixels; a deferred start so a finished animation has returned.
        function startRun() {
            root.trace("startRun text=" + JSON.stringify(root.tickerText.length) + " running=" + rotation.running
                       + " paused=" + rotation.paused + " cells=" + rep.textCells + " rep=" + rep.width + "x" + rep.height);
            if (root.tickerText.length === 0 || rotation.running) return;
            if (field.cols <= 0) { Qt.callLater(startRun); return; }
            rotation.from = 0;
            rotation.to = (field.cols + rep.textCells) * field.scale;
            field.offset = 0;
            rotation.start();
        }
        Component.onCompleted: { root.charAdvance = advanceCells * pitch; Qt.callLater(startRun); }

        // ⚑ HYPERLINKS (W40). Hovering the board PAUSES the rotation so a link can
        // be aimed at — the board resumes when the pointer leaves — and a tap
        // hit-tests the pointer's x against the text's left edge and the character
        // advance; a link run opens externally. A CHOICE, NOT A GIVEN (the offscreen
        // pointer rests at (0,0); a pointer parked on the panel does the same).
        HoverHandler {
            id: boardHover
            enabled: root.cfgHoverPause && root.tickerText.length > 0
            onHoveredChanged: rotation.paused = hovered && rotation.running
        }
        TapHandler {
            enabled: root.cfgOpenLinks
            onTapped: (eventPoint, button) => root.tapAt(eventPoint.position.x)
        }
        // ⚑ ONE ROTATION PER RUN, and the ring swaps at its END. A finite run that
        // restarts itself is where "a full rotation" is a real event.
        NumberAnimation {
            id: rotation
            target: field; property: "offset"
            // from / to are SET by startRun (see above); nothing binds them.
            // speed scales with length so long feeds don't crawl; the settings'
            // speed factor divides the duration
            duration: Math.max(1500, (rep.width + rep.textWidth) * 12 / root.cfgSpeed)
            loops: 1
            onRunningChanged: root.boardRunning = running
            onPausedChanged: root.boardPaused = paused
            onFinished: {
                root.trace("finished x=" + root.boardRawX);
                root.swapRing();
                // the next run starts after this one has fully returned; if the
                // ring drained, the ticker is empty and startRun declines
                Qt.callLater(rep.startRun);
            }
        }

        property real matrixHeight: root.matrix.rows * pitch
    }
}
