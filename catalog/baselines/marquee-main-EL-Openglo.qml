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
    property color litColor: "#99ffeb"
    property color ghostColor: "#7ed3c3"
    property color voidColor: "#081411"
    // the unlit dot field's opacity — the palette's solved ghost_alpha, passed to
    // every MatrixChar below in place of the component's authored 0.28. Whether a
    // DOT FIELD at this alpha reads as the same texture as strokes do is
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
    property string pendingText: ""       // PENDING: what scrolls after this rotation
    property bool haveModel: false

    function swapRing() {
        root.tickerText = root.pendingText;
        root.tickerRuns = root.pendingRuns;
    }

    // ⚑ BODIES ARE MARKUP (W39). The spec allows <b> <i> <u> <a> <img>; Plasma
    // passes its sanitised subset through with <br> and entities; un-stripped,
    // the TAGS scrolled across the board as text. Body.parseBody (marquee-body.js,
    // shipped beside this file and run headless by check_marquee_body) returns
    // the plain text plus STYLE RUNS (bold / italic / underline / link / colour
    // spans), kept here as data for the styling half (relations.md §5). Nothing
    // reads the runs yet; the text is what scrolls.
    property var tickerRuns: []
    property var pendingRuns: []

    NotificationManager.Notifications {
        id: notifModel
        showNotifications: true
        showJobs: true
        // newest first so the ticker leads with the latest
        sortMode: NotificationManager.Notifications.SortByDate
        groupMode: NotificationManager.Notifications.GroupDisabled
        Component.onCompleted: root.haveModel = true
        onCountChanged: root.rebuild()
    }

    function rebuild() {
        var text = "", runs = [];
        var n = Math.min(notifModel.count, root.cfgMaxItems);
        var sep = "     •     ";
        for (var i = 0; i < n; i++) {
            var idx = notifModel.index(i, 0);
            var app = notifModel.data(idx, NotificationManager.Notifications.ApplicationNameRole);
            var sum = notifModel.data(idx, NotificationManager.Notifications.SummaryRole);
            var body = notifModel.data(idx, NotificationManager.Notifications.BodyRole);
            var seg = "";
            if (app) seg += app + ": ";
            if (sum) seg += sum;
            if (body) seg += " — " + body;
            var parsed = Body.parseBody(seg);
            var plain = parsed.text.replace(/\s+/g, " ").trim();
            if (!plain.length) continue;
            if (text.length) text += sep;
            var base = text.length;
            // the runs keep their offsets into the joined ring text
            for (var r = 0; r < parsed.runs.length; r++) {
                var run = parsed.runs[r];
                runs.push({ start: base + run.start, end: base + run.end, bold: run.bold,
                            italic: run.italic, underline: run.underline, link: run.link, color: run.color });
            }
            text += plain;
        }
        root.pendingText = text;               // empty -> the ring drains to idle
        root.pendingRuns = runs;
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
            Repeater {
                model: root.tickerText.split("")
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
                running: marquee.visible
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
