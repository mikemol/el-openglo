// EL Openglo — SDDM greeter (W66): the segment display's FOURTH MOUNT, after
// the clock plasmoid, the notification marquee and the live wallpaper.
//
// ⚑ A GREETER HAS NO KIRIGAMI AND NO PLASMA, so nothing here is BOUND to a
// colour scheme the way the other mounts are (⊕ONE-THEME). The palette is BAKED
// per variant from make_schemes.GRID by make_sddm.py — one theme directory per
// variant, each a separate entry in the SDDM picker. SegmentChar imports only
// QtQuick and QtQuick.Effects, which is what makes this mount possible at all.
//
// ⚑ A GREETER IS AN AUTH SURFACE. The wiring mirrors the stock breeze theme
// (/usr/share/sddm/themes/breeze/Main.qml, Login.qml, SessionButton.qml):
//   user     — userModel, role `name`; starts at userModel.lastIndex (breeze Main.qml:178)
//   session  — sessionModel, role `name`; starts at sessionModel.lastIndex (SessionButton.qml:22)
//   login    — sddm.login(user, password, sessionIndex) (breeze Main.qml:243)
//   failure  — Connections on sddm.onLoginFailed (breeze Main.qml:513-521, Login.qml:134-140)
//   focus    — the password field, re-forced after 200 ms (breeze Main.qml:163-172)
// The controls are QtQuick.Controls.Basic: a fixed style, so the palette below is
// what draws them whatever QT_QUICK_CONTROLS_STYLE the greeter inherits.
import QtQuick
import QtQuick.Controls.Basic

Control {
    id: root
    width: 1600
    height: 900

    // --- the variant's palette, READ from make_schemes.GRID at emit time -------
    readonly property color voidColor: "$ground"      // [Colors:View] BackgroundNormal (view)
    readonly property color litColor: "$lit"          // ForegroundNormal (fg)
    readonly property color ghostColor: "$ghost"      // ForegroundInactive (fg_in)
    readonly property color fieldColor: "$field"      // [Colors:Button] BackgroundNormal (button)
    readonly property color focusColor: "$focus"      // DecorationFocus (focus)
    readonly property color negativeColor: "$negative" // ForegroundNegative (neg)
    // the ghost pass opacity, SOLVED for a glanced-at surface (ghost_alpha_glanced):
    // the login clock is ambient, like the lock-screen mount of the live wallpaper
    readonly property real ghostAlpha: $ghostAlpha

    // metrics in U (H = 4U), the substrate's (segment_topology.MODULE_METRICS)
    readonly property real pitch: $pitch
    readonly property real colonAdvance: $colonAdvance
    readonly property real dotR: $dotR
    readonly property real strokeBase: $strokeBase

$tables

    palette.window: root.voidColor
    palette.windowText: root.litColor
    palette.base: root.fieldColor
    palette.alternateBase: root.fieldColor
    palette.text: root.litColor
    palette.button: root.fieldColor
    palette.buttonText: root.litColor
    palette.highlight: root.focusColor
    palette.highlightedText: root.voidColor
    palette.placeholderText: root.ghostColor
    palette.mid: root.ghostColor
    palette.dark: root.ghostColor
    palette.light: root.fieldColor

    background: Rectangle { color: root.voidColor }

    property string failure: ""

    function startLogin() {
        const user = userSelector.count > 0 ? userSelector.currentText : userNameField.text;
        root.failure = "";
        sddm.login(user, passwordField.text, sessionSelector.currentIndex);
    }

    // --- the clock: the display's fourth mount --------------------------------
    property string timeStr: "00:00"
    property bool colonOn: true
    function tick() {
        const d = new Date();
        const h = d.getHours(), m = d.getMinutes();
        root.timeStr = (h < 10 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m;
        root.colonOn = !root.colonOn;
    }
    Timer { interval: 1000; running: true; repeat: true; triggeredOnStart: true; onTriggered: root.tick() }

    Row {
        id: face
        objectName: "clockFace"
        anchors.horizontalCenter: parent.horizontalCenter
        y: Math.round(parent.height * 0.12)
        // the same fit as the live wallpaper: a length in U halves into segLen
        readonly property real gapRatio: root.pitch / 2 - 1.0
        readonly property real colonRatio: root.colonAdvance / 2
        property real cellLen: Math.max(6, Math.floor(Math.min(
            parent.width * 0.4 / (4 + 3 * gapRatio + colonRatio),
            parent.height * 0.36 / 2)))
        spacing: Math.round(cellLen * gapRatio)
        Repeater {
            model: 4
            SegmentChar {
                required property int index
                segGeom: root.segGeom
                digSegs: root.digSegs
                ch: root.timeStr.charAt(index < 2 ? index : index + 1)
                insertColon: index === 1
                colonOn: root.colonOn
                segLen: face.cellLen
                segThick: Math.max(2, Math.floor(face.cellLen * root.strokeBase * 0.5))
                dotSize: Math.max(2, face.cellLen * root.dotR)
                colonAdvance: face.colonRatio
                cellGap: face.spacing
                litColor: root.litColor
                ghostColor: root.ghostColor
                ghostAlpha: root.ghostAlpha
            }
        }
    }

    // --- the auth block ---------------------------------------------------------
    Column {
        id: form
        width: Math.min(360, root.width * 0.8)
        anchors.horizontalCenter: parent.horizontalCenter
        y: Math.round(root.height * 0.58)
        spacing: 10

        ComboBox {
            id: userSelector
            objectName: "userSelector"
            width: parent.width
            model: userModel
            textRole: "name"
            visible: count > 0
            currentIndex: userModel.lastIndex >= 0 ? userModel.lastIndex : 0
            onActivated: passwordField.forceActiveFocus()
        }
        // SDDM may hand a theme an empty userModel (needsFullUserModel, hidden
        // users): then the user is typed, as breeze's "Other…" prompt does
        TextField {
            id: userNameField
            objectName: "userNameField"
            width: parent.width
            visible: userSelector.count === 0
            text: userModel.lastUser !== undefined ? userModel.lastUser : ""
            placeholderText: "Username"
            onAccepted: passwordField.forceActiveFocus()
        }
        TextField {
            id: passwordField
            objectName: "passwordField"
            width: parent.width
            echoMode: TextInput.Password
            placeholderText: "Password"
            focus: true
            onAccepted: root.startLogin()
        }
        Button {
            id: loginButton
            objectName: "loginButton"
            width: parent.width
            text: "Log In"
            onClicked: root.startLogin()
            Keys.onReturnPressed: clicked()
            Keys.onEnterPressed: clicked()
        }
        Text {
            id: failureMessage
            objectName: "failureMessage"
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            color: root.negativeColor
            text: root.failure
            visible: text.length > 0
        }
    }

    // --- footer: session and power, as breeze's footer carries them -------------
    Row {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 12
        spacing: 8
        layoutDirection: Qt.RightToLeft

        ComboBox {
            id: sessionSelector
            objectName: "sessionSelector"
            width: 240
            model: sessionModel
            textRole: "name"
            Component.onCompleted: currentIndex = sessionModel.lastIndex
            onActivated: passwordField.forceActiveFocus()
        }
        Button { text: "Shut Down"; visible: sddm.canPowerOff; onClicked: sddm.powerOff() }
        Button { text: "Restart"; visible: sddm.canReboot; onClicked: sddm.reboot() }
        Button { text: "Sleep"; visible: sddm.canSuspend; onClicked: sddm.suspend() }
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            root.failure = "Login Failed";
            passwordField.selectAll();
            passwordField.forceActiveFocus();
        }
        function onLoginSucceeded() {
            form.opacity = 0;
        }
    }

    // SDDM activates the window after it is shown; force focus once it is (breeze Main.qml:163-172)
    Timer {
        interval: 200
        running: true
        onTriggered: passwordField.forceActiveFocus()
    }
}
