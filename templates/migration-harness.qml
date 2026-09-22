// migration-harness.qml — a FAKE of the Plasma desktop-scripting API, enough for
// templates/one-theme-update.js, populated like the operator's appletsrc of
// 2026-09-22 (a desktop on a legacy live-wallpaper id; a panel with a legacy
// clock and marquee among stock widgets). check_migration runs the generated
// update script inside it and reads the shell afterwards.
import QtQuick
QtObject {
    id: shell
    property var nextId: 100

    function makeWidget(cont, type, x, y, w, h, config) {
        var wd = { type: type, geometry: { x: x, y: y, width: w, height: h }, config: config || {},
                   currentConfigGroup: [], id: shell.nextId++ };
        wd.readConfig = function (k) { return wd.config[k]; };
        wd.writeConfig = function (k, v) { wd.config[k] = String(v); };
        wd.reloadConfig = function () {};
        wd.remove = function () { cont.widgets = cont.widgets.filter(function (o) { return o.id !== wd.id; }); };
        return wd;
    }
    function makeContainment(kind, wallpaper) {
        var cont = { kind: kind, wallpaperPlugin: wallpaper, widgets: [] };
        Object.defineProperty(cont, "widgetIds", { get: function () { return cont.widgets.map(function (w) { return w.id; }); } });
        cont.widgetById = function (id) { for (var i = 0; i < cont.widgets.length; i++) if (cont.widgets[i].id === id) return cont.widgets[i]; return null; };
        cont.addWidget = function (type, x, y, w, h) { var wd = shell.makeWidget(cont, type, x, y, w, h, {}); cont.widgets.push(wd); return wd; };
        return cont;
    }

    property var desktop: makeContainment("desktop", "org.el.openglo.live.elazure")
    property var panel: makeContainment("panel", "org.kde.image")

    Component.onCompleted: {
        panel.widgets.push(makeWidget(panel, "org.kde.plasma.kickoff", 0, 0, 40, 30, {}));
        panel.widgets.push(makeWidget(panel, "org.el.segclock.elazure", 200, 0, 90, 30, { use24h: "true", bloom: "1.5" }));
        panel.widgets.push(makeWidget(panel, "org.el.notifymarquee.elazure", 300, 0, 420, 30, { hoverPause: "false", speed: "1.5" }));
        panel.widgets.push(makeWidget(panel, "org.kde.plasma.systemtray", 800, 0, 100, 30, {}));
        // the script's globals: the desktop-scripting API surface it uses
        var api = { desktops: function () { return [shell.desktop]; }, panels: function () { return [shell.panel]; } };
        var src = Qt.include ? null : null;
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "update.js", false);
        xhr.send();
        var fn = new Function("desktops", "panels", xhr.responseText);
        fn(api.desktops, api.panels);
        var out = {
            desktops: [{ wallpaper: shell.desktop.wallpaperPlugin }],
            panels: [{ widgets: shell.panel.widgets.map(function (w) {
                return { type: w.type, config: w.config, geometry: [w.geometry.x, w.geometry.y, w.geometry.width, w.geometry.height] }; }) }]
        };
        console.log("RESULT " + JSON.stringify(out));
        Qt.quit();
    }
}
