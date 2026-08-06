import sys
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine
from basejump.ui_kde.models import OverlayServiceModel

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
overlayService = OverlayServiceModel()
engine.rootContext().setContextProperty("overlayService", overlayService)
engine.loadData(b"""
import QtQuick
import QtQuick.Controls

ApplicationWindow {
    visible: true
    Component.onCompleted: {
        console.log("Calling...");
        try {
            var ret = overlayService.createOverlaySet("Test", "Desc", ["pkg1"], [], []);
            console.log("Result:", ret);
        } catch(e) {
            console.log("Error:", e);
        }
        Qt.quit();
    }
}
""")
sys.exit(app.exec())
