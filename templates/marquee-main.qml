import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
// PUBLIC notification model (libnotificationmanager) — the same feed the stock
// applet reads. NOT the deprecated org.kde.plasma.private.notifications.
import org.kde.notificationmanager as NotificationManager
// the body-markup parser, shipped beside this file (W39)
import "marquee-body.js" as Body

PlasmoidItem {
    id: root
    property color litColor: "$lit"
    property color ghostColor: "$ghost"
    property color voidColor: "$ground"
    // the unlit dot field's opacity — the palette's solved ghost_alpha, passed to
    // every MatrixChar below in place of the component's authored 0.28. Whether a
    // DOT FIELD at this alpha reads as the same texture as strokes do is
    // ⊕GHOST-DENSITY's question, still open; the relation itself is one.
    property real ghostAlpha: $ghostAlpha

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

    function liveIds() {
        var ids = [];
        for (var i = 0; i < notifModel.count; i++)
            ids.push(notifModel.data(notifModel.index(i, 0), NotificationManager.Notifications.IdRole));
        return ids;
    }

    function swapRing() {
        var next = Body.ringNext(root.queue, root.liveIds(), root.cfgMaxItems);
        root.queue = next.queue;
        var joined = Body.ringJoin(next.ring, "     •     ");
        root.tickerText = joined.text;         // empty -> the ring drains to idle
        root.tickerRuns = joined.runs;
    }

    // ⚑ BODIES ARE MARKUP (W39). The spec allows <b> <i> <u> <a> <img>; Plasma
    // passes its sanitised subset through with <br> and entities; un-stripped,
    // the TAGS scrolled across the board as text. Body.parseBody (marquee-body.js,
    // shipped beside this file and run headless by check_marquee_body) returns
    // the plain text plus STYLE RUNS (bold / italic / underline / link / colour
    // spans), read below as a fuller dot, a gated hue, an underline, a href.
    property var tickerRuns: []

    // ⚑ THE SOLVED HUE TABLE (relations.md §5a; make_palette.hue_table, gated by
    // check_rehue). Twelve buckets, index = hue / 30; a bucket the gate refused
    // already holds the lit token, so a lookup can never produce an unreadable
    // colour. The widget does no colour arithmetic beyond finding the bucket.
    property var hueTable: $hueTable
    // bold is a fuller dot: the clock's weight ratio, on the dot's area
    readonly property real boldFill: 1.15

    function runAt(i) {
        var rs = root.tickerRuns;
        for (var k = 0; k < rs.length; k++)
            if (i >= rs[k].start && i < rs[k].end) return rs[k];
        return null;
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
        var m = /^#([0-9a-f]{6})$$/.exec(s);
        if (!m) {
            var m3 = /^#([0-9a-f])([0-9a-f])([0-9a-f])$$/.exec(s);
            if (!m3) return -1;
            s = "#" + m3[1] + m3[1] + m3[2] + m3[2] + m3[3] + m3[3];
            m = /^#([0-9a-f]{6})$$/.exec(s);
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
        onCountChanged: root.rebuild()
        // a replace (same id, new text) changes no count; it changes data
        onDataChanged: root.rebuild()
    }

    // the model changed: upsert every live notification into the queue. A new id
    // is owed a rotation; a known id with new text (a replace) is owed one again;
    // an unchanged id is left as it stands. The ring is NOT touched here.
    function rebuild() {
        var q = root.queue;
        var known = {};
        for (var k = 0; k < q.length; k++) known[q[k].id] = q[k].text;
        for (var i = 0; i < notifModel.count; i++) {
            var idx = notifModel.index(i, 0);
            var id = notifModel.data(idx, NotificationManager.Notifications.IdRole);
            var app = notifModel.data(idx, NotificationManager.Notifications.ApplicationNameRole);
            var sum = notifModel.data(idx, NotificationManager.Notifications.SummaryRole);
            var body = notifModel.data(idx, NotificationManager.Notifications.BodyRole);
            // the summary is PLAIN, the body is markup (W45): Body.joinItem
            var item = Body.joinItem(app, sum, body);
            if (!item.text.length) continue;
            if (id in known && known[id] === item.text) continue;
            q = Body.queueUpsert(q, { id: id, text: item.text, runs: item.runs });
        }
        root.queue = q;
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
    property var registry: $registry
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

        // ⚑ THE FIELD IS THE HARDWARE.  Every unlit LED, bezel to bezel, drawn
        // once and never moved; the idle face IS this field. (Operator, live
        // 2026-09-22: the pips scrolled with the glyphs and stopped at the
        // message's end — the ghost had been drawn per character.)
        MatrixField {
            id: field
            anchors.fill: parent
            visible: root.cfgShowField
            rows: root.matrix.rows
            u: rep.pitch
            dotFill: root.cfgDotFill
            ghostColor: root.ghostColor
            ghostOpacity: root.cfgGhostAlpha
        }

        // idle text (settings), lit on the field, centred and snapped to the pitch
        Row {
            visible: root.tickerText.length === 0 && root.cfgIdleText.length > 0
            spacing: rep.pitch
            y: (parent.height - rep.matrixHeight) / 2
            x: Math.round(((rep.width - width) / 2) / rep.pitch) * rep.pitch
            Repeater {
                model: root.cfgIdleText.split("")
                MatrixChar {
                    font: root.matrixFont
                    cols: root.matrix.cols; rows: root.matrix.rows
                    ch: modelData
                    u: rep.pitch
                    dotFill: root.cfgDotFill
                    litColor: root.litColor
                    ghostColor: root.ghostColor
                    ghostOpacity: root.cfgGhostAlpha
                    showGhost: false
                }
            }
        }

        // the marquee: the LIT dots scroll right-to-left OVER the field. The
        // characters draw no ghost of their own, and x is snapped to the field's
        // pitch so every lit dot lands on a field cell rather than between two.
        Row {
            id: marquee
            visible: root.tickerText.length > 0
            spacing: rep.pitch
            y: (parent.height - rep.matrixHeight) / 2
            property real rawX: rep.width
            x: Math.round(rawX / rep.pitch) * rep.pitch
            // ⚑ THE ROTATION IS STARTED, NEVER BOUND (operator, live 2026-09-22:
            // "doesn't respond to notifications at all"). `running: marquee.visible`
            // was a binding that the animation's own completion OVERWROTE with
            // false — Qt assigns `running` when a finite animation ends, which
            // discards the binding — so after the ring first drained to idle, a
            // new notification made the Row visible but nothing ever ran again,
            // and rawX sat parked off the left edge. Now the Row starts the run
            // itself each time it becomes visible while nothing is running.
            function startRun() {
                if (!marquee.visible || rotation.running) return;
                marquee.rawX = rep.width;
                rotation.start();
            }
            onVisibleChanged: startRun()
            Component.onCompleted: startRun()
            Repeater {
                model: root.tickerText.split("")
                MatrixChar {
                    required property int index
                    required property string modelData
                    readonly property var run: root.runAt(index)
                    font: root.matrixFont
                    cols: root.matrix.cols; rows: root.matrix.rows
                    ch: modelData
                    u: rep.pitch
                    // a bold run is a fuller dot (area, not opacity); a coloured run
                    // is the solved table's bucket, never the sender's literal
                    dotFill: (run && run.bold) ? Math.min(1.0, root.cfgDotFill * root.boldFill) : root.cfgDotFill
                    litColorOverride: root.overrideFor(run)
                    // a link (or a <u> run) is underlined: its descent row lit (W40)
                    underline: run !== null && (run.link.length > 0 || run.underline)
                    litColor: root.litColor
                    ghostColor: root.ghostColor
                    ghostOpacity: root.cfgGhostAlpha
                    showGhost: false
                }
            }
            // ⚑ HYPERLINKS (W40; operator: "that would be awesome"). Hovering the
            // board PAUSES the rotation so a link can be aimed at — a reader's
            // affordance, the board resumes when the pointer leaves — and a tap
            // hit-tests the pointer's x against the character advance to the run
            // under it; a link run opens externally. The parser already carries
            // the href (marquee-body.js); this is the only place it is read.
            HoverHandler {
                id: boardHover
                onHoveredChanged: rotation.paused = hovered && rotation.running
            }
            TapHandler {
                enabled: root.cfgOpenLinks
                onTapped: (eventPoint, button) => {
                    var idx = Math.floor(eventPoint.position.x / (rep.cellW + rep.pitch));
                    var run = root.runAt(idx);
                    if (run && run.link.length > 0) Qt.openUrlExternally(run.link);
                }
            }
            // ⚑ ONE ROTATION PER RUN, and the ring swaps at its END. Infinite loops
            // would re-read `to` and the model mid-flight; a finite run that
            // restarts itself is where "a full rotation" is a real event.
            NumberAnimation {
                id: rotation
                target: marquee; property: "rawX"
                from: rep.width; to: -marquee.width
                // speed scales with length so long feeds don't crawl; the
                // settings' speed factor divides the duration
                duration: Math.max(1500, (rep.width + marquee.width) * 12 / root.cfgSpeed)
                loops: 1
                onFinished: {
                    root.swapRing();
                    if (root.tickerText.length > 0) {
                        marquee.rawX = rep.width;
                        rotation.restart();
                    }
                }
            }
        }

        property real matrixHeight: root.matrix.rows * pitch
    }
}
