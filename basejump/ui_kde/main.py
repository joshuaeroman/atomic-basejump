import sys
import os

os.environ["QT_QUICK_CONTROLS_STYLE"] = "org.kde.desktop"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QIcon

from basejump.ui_kde.models import AppInfoModel, OstreeBackendModel, ImageRegistryServiceModel, SettingsManagerModel, OverlayServiceModel

def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("joshuaroman")
    app.setOrganizationDomain("github.com")
    app.setApplicationName("atomicbasejump")
    app.setApplicationDisplayName("Atomic Basejump")
    app.setDesktopFileName("io.github.joshuaroman.AtomicBasejump")
    app.setWindowIcon(QIcon.fromTheme("io.github.joshuaroman.AtomicBasejump"))

    backend = OstreeBackendModel()
    imageRegistry = ImageRegistryServiceModel()
    overlayService = OverlayServiceModel()
    appInfo = AppInfoModel()
    settingsManager = SettingsManagerModel(backend)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("imageRegistry", imageRegistry)
    engine.rootContext().setContextProperty("overlayService", overlayService)
    engine.rootContext().setContextProperty("appInfo", appInfo)
    engine.rootContext().setContextProperty("settingsManager", settingsManager)

    # Load from local filesystem
    qml_file = os.path.join(os.path.dirname(__file__), 'qml', 'Main.qml')
    engine.load(QUrl.fromLocalFile(qml_file))

    if not engine.rootObjects():
        sys.exit(-1)

    ret = app.exec()
    del engine
    sys.exit(ret)
if __name__ == '__main__':
    main()
