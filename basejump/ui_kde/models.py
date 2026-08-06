from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot, QVariant
from basejump.core.appinfo import AppInfo
import threading

class AppInfoModel(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._core = AppInfo()

    @pyqtProperty(str, constant=True)
    def version(self): return self._core.version

    @pyqtProperty(str, constant=True)
    def buildTimestamp(self): return self._core.build_timestamp

    @pyqtProperty(str, constant=True)
    def displayName(self): return self._core.display_name

    @pyqtProperty(str, constant=True)
    def homepage(self): return self._core.homepage

    @pyqtProperty(str, constant=True)
    def license(self): return self._core.license

from basejump.core.ostree import OstreeBackend

class OstreeBackendModel(QObject):
    deploymentsChanged = pyqtSignal()
    statusChanged = pyqtSignal()
    transactionStateChanged = pyqtSignal()
    transactionProgressChanged = pyqtSignal()
    transactionMessageChanged = pyqtSignal()
    transactionLogChanged = pyqtSignal()
    lastErrorChanged = pyqtSignal()
    operationFailed = pyqtSignal(str, str)
    notificationRequested = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._core = OstreeBackend(self._notify_core)
        self.refreshStatus()

    def _notify_core(self):
        self.deploymentsChanged.emit()
        self.statusChanged.emit()
        self.transactionStateChanged.emit()
        self.transactionProgressChanged.emit()
        self.transactionMessageChanged.emit()
        self.transactionLogChanged.emit()
        self.lastErrorChanged.emit()

    def setImageRegistry(self, registry):
        self._registry = registry

    @pyqtProperty('QVariantList', notify=deploymentsChanged)
    def deployments(self): return self._core.deployments

    @pyqtProperty('QVariantMap', notify=statusChanged)
    def bootedDeployment(self): return self._core.bootedDeployment

    @pyqtProperty('QVariantMap', notify=statusChanged)
    def pendingDeployment(self): return self._core.pendingDeployment

    @pyqtProperty('QVariantMap', notify=statusChanged)
    def rollbackDeployment(self): return self._core.rollbackDeployment

    @pyqtProperty(bool, notify=statusChanged)
    def updateAvailable(self): return self._core.updateAvailable

    @pyqtProperty(bool, notify=statusChanged)
    def rebootRequired(self): return self._core.rebootRequired

    @pyqtProperty(bool, notify=transactionStateChanged)
    def transactionInProgress(self): return self._core.transactionInProgress

    @pyqtProperty(int, notify=transactionProgressChanged)
    def transactionProgress(self): return self._core.transactionProgress

    @pyqtProperty(str, notify=transactionMessageChanged)
    def transactionMessage(self): return self._core.transactionMessage

    @pyqtProperty(str, notify=transactionMessageChanged)
    def currentTask(self): return self._core.currentTask

    @pyqtProperty(str, notify=transactionLogChanged)
    def transactionLog(self): return self._core.transactionLog

    @pyqtProperty(str, notify=lastErrorChanged)
    def lastError(self): return self._core.lastError

    @pyqtProperty(str, notify=statusChanged)
    def statusBannerMessage(self): return self._core.statusBannerMessage

    @pyqtProperty(str, notify=statusChanged)
    def statusBannerType(self): return self._core.statusBannerType

    @pyqtProperty(str, notify=statusChanged)
    def currentOsName(self): return self._core.currentOsName

    @pyqtProperty(str, notify=statusChanged)
    def bootedDesktopFamily(self): return self._core.bootedDesktopFamily

    @pyqtProperty(bool, notify=statusChanged)
    def severeUpdateAvailable(self): return self._core.severeUpdateAvailable

    @pyqtProperty(bool, notify=statusChanged)
    def plasmaLoginRepairAvailable(self): return self._core.plasmaLoginRepairAvailable

    @pyqtSlot()
    def refreshStatus(self):
        self._core.refresh_status()
        self.deploymentsChanged.emit()
        self.statusChanged.emit()

    @pyqtSlot()
    def checkForUpdates(self):
        self._core.checkForUpdates()

    @pyqtSlot()
    def upgradeSystem(self):
        self._core.upgradeSystem()

    @pyqtSlot()
    def rollbackSystem(self):
        self._core.rollbackSystem()

    @pyqtSlot(str, 'QVariantMap')
    def rebaseSystem(self, refspec, options=None):
        self._core.rebaseSystem(refspec, options)

    @pyqtSlot(int)
    def pinDeployment(self, index):
        self._core.pinDeployment(index)

    @pyqtSlot(int)
    def unpinDeployment(self, index):
        self._core.unpinDeployment(index)

    @pyqtSlot()
    def rebootSystem(self):
        self._core.rebootSystem()

    @pyqtSlot(str, result='QVariantList')
    def searchPackages(self, term):
        return self._core.searchPackages(term)

    @pyqtSlot(result='QVariantList')
    def getDeploymentPackages(self):
        return self._core.getDeploymentPackages()

    @pyqtSlot('QVariantList', 'QVariantList', 'QVariantList')
    def applyOverlaySet(self, layered, local, removed):
        self._core.applyOverlaySet(layered, local, removed)

    @pyqtSlot()
    def resetOverlays(self):
        self._core.resetOverlays()

    @pyqtSlot('QVariantList', 'QVariantList', 'QVariantList')
    def queuePendingOverlaySet(self, layered, local, removed):
        self._core.queuePendingOverlaySet(layered, local, removed)

    @pyqtSlot()
    def queuePendingOverlayReset(self):
        self._core.queuePendingOverlayReset()

    @pyqtSlot()
    def clearTransactionLog(self):
        self._core.clearTransactionLog()

    @pyqtSlot(str, result=bool)
    def needsPlasmaLoginPrep(self, targetRefOrImage):
        return self._core.needsPlasmaLoginPrep(targetRefOrImage)

    @pyqtSlot(bool)
    def prepPlasmaLoginAccounts(self, includeStagedDeployment=False):
        self._core.prepPlasmaLoginAccounts(includeStagedDeployment)

from basejump.core.registry import ImageRegistryService

class ImageRegistryServiceModel(QObject):
    loadingTagsChanged = pyqtSignal()
    loadingBuildDateChanged = pyqtSignal()
    tagsFetched = pyqtSignal(str, 'QVariantList', 'QVariantList', 'QVariantList')
    tagBuildDateFetched = pyqtSignal(str, str, str)
    fetchError = pyqtSignal(str, str)
    buildDateError = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._core = ImageRegistryService()

    @pyqtProperty(bool, notify=loadingTagsChanged)
    def loadingTags(self): return self._core.loading_tags

    @pyqtProperty(bool, notify=loadingBuildDateChanged)
    def loadingBuildDate(self): return self._core.loading_build_date

    @pyqtSlot(result='QVariantList')
    def sources(self): return self._core.sources()

    @pyqtSlot(str, result='QVariantList')
    def typesForSource(self, sourceId): return self._core.typesForSource(sourceId)

    @pyqtSlot(str)
    def fetchTags(self, imageRef):
        self._core.loading_tags = True
        self.loadingTagsChanged.emit()
        self._core.fetchTags(
            imageRef,
            lambda ref, tags, versions, dates: self._tags_done(ref, tags, versions, dates),
            lambda ref, error: self._tags_error(ref, error),
        )

    def _tags_done(self, imageRef, tags, versions, dates):
        self.tagsFetched.emit(imageRef, tags, versions, dates)
        self._core.loading_tags = False
        self.loadingTagsChanged.emit()

    def _tags_error(self, imageRef, error):
        self.fetchError.emit(imageRef, error)
        self._core.loading_tags = False
        self.loadingTagsChanged.emit()

    @pyqtSlot(str, str)
    def fetchTagBuildDate(self, imageRef, tag):
        self._core.loading_build_date = True
        self.loadingBuildDateChanged.emit()
        self._core.fetchTagBuildDate(
            imageRef,
            tag,
            lambda ref, selected, date: self._build_date_done(ref, selected, date),
            lambda ref, selected, error: self._build_date_error(ref, selected, error),
        )

    def _build_date_done(self, imageRef, tag, date):
        self.tagBuildDateFetched.emit(imageRef, tag, date)
        self._core.loading_build_date = False
        self.loadingBuildDateChanged.emit()

    def _build_date_error(self, imageRef, tag, error):
        self.buildDateError.emit(imageRef, tag, error)
        self._core.loading_build_date = False
        self.loadingBuildDateChanged.emit()

    @pyqtSlot(str, str, bool, result=str)
    def constructRefSpec(self, imageRef, tag, requireSignature=True): return self._core.constructRefSpec(imageRef, tag, requireSignature)

    @pyqtSlot(str, result=bool)
    def isUblueRef(self, refOrImage): return self._core.isUblueRef(refOrImage)

    @pyqtSlot(str, result=bool)
    def isSignedTransport(self, refspec): return self._core.isSignedTransport(refspec)

    @pyqtSlot(str, result=bool)
    def preferSignedDefault(self, currentRefspec):
        return self._core.isUblueRef(currentRefspec) and self._core.isSignedTransport(currentRefspec)

    @pyqtSlot(str, result=bool)
    def allowsSignedUblueTarget(self, currentRefspec): return self._core.allowsSignedUblueTarget(currentRefspec)

    @pyqtSlot(str, result=str)
    def imageRefFromRefspec(self, refspec): return self._core.imageRefFromRefspec(refspec)

    @pyqtSlot(str, result=str)
    def tagFromRefspec(self, refspec): return self._core.tagFromRefspec(refspec)

    @pyqtSlot(str, result=bool)
    def isStreamTag(self, tag): return self._core.isStreamTag(tag)

    @pyqtSlot(str, result='QVariantMap')
    def matchImageRef(self, imageRefOrRefspec): return self._core.matchImageRef(imageRefOrRefspec)

    @pyqtSlot(str, result='QVariantMap')
    def resolveBootedSelection(self, refspec): return self._core.resolveBootedSelection(refspec)

    @pyqtSlot(str, result=str)
    def desktopFamilyFromRef(self, refOrImage): return self._core.desktopFamilyFromRef(refOrImage)

    @pyqtSlot(str, str, result=bool)
    def needsPlasmaLoginPrep(self, bootedRefOrImage, targetRefOrImage):
        return (
            self._core.desktopFamilyFromRef(bootedRefOrImage) != "plasma"
            and self._core.desktopFamilyFromRef(targetRefOrImage) == "plasma"
        )

from basejump.core.settings import SettingsManager

class SettingsManagerModel(QObject):
    showTrayIconChanged = pyqtSignal()
    enableNotificationsChanged = pyqtSignal()
    notifyOnStagedUpdateChanged = pyqtSignal()
    systemAutoUpdateChanged = pyqtSignal()
    appAutoUpdateChanged = pyqtSignal()
    severeOnlyChanged = pyqtSignal()
    autoStageUpdatesChanged = pyqtSignal()
    lastCheckTimeChanged = pyqtSignal()
    uiThemeChanged = pyqtSignal()

    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._core = SettingsManager()
        threading.Thread(
            target=self._refresh_system_auto_update_sync, daemon=True
        ).start()

    @pyqtProperty(str, notify=uiThemeChanged)
    def uiTheme(self): return self._core.uiTheme

    @uiTheme.setter
    def uiTheme(self, value): 
        self._core.uiTheme = value
        self.uiThemeChanged.emit()

    @pyqtProperty(bool, notify=showTrayIconChanged)
    def showTrayIcon(self): return self._core.showTrayIcon

    @showTrayIcon.setter
    def showTrayIcon(self, value): self._core.showTrayIcon = value; self.showTrayIconChanged.emit()

    @pyqtProperty(bool, notify=enableNotificationsChanged)
    def enableNotifications(self): return self._core.enableNotifications

    @enableNotifications.setter
    def enableNotifications(self, value): self._core.enableNotifications = value; self.enableNotificationsChanged.emit()

    @pyqtProperty(bool, notify=notifyOnStagedUpdateChanged)
    def notifyOnStagedUpdate(self): return self._core.notifyOnStagedUpdate

    @notifyOnStagedUpdate.setter
    def notifyOnStagedUpdate(self, value): self._core.notifyOnStagedUpdate = value; self.notifyOnStagedUpdateChanged.emit()

    @pyqtProperty(bool, notify=systemAutoUpdateChanged)
    def systemAutoUpdateEnabled(self): return self._core.systemAutoUpdateEnabled

    @pyqtProperty(str, notify=systemAutoUpdateChanged)
    def systemAutoUpdateStatus(self): return self._core.systemAutoUpdateStatus

    @pyqtProperty(bool, notify=systemAutoUpdateChanged)
    def systemAutoUpdateChecking(self): return self._core.systemAutoUpdateChecking

    @pyqtProperty(bool, notify=appAutoUpdateChanged)
    def appAutoUpdateEnabled(self): return self._core.appAutoUpdateEnabled

    @appAutoUpdateEnabled.setter
    def appAutoUpdateEnabled(self, value): self._core.appAutoUpdateEnabled = value; self.appAutoUpdateChanged.emit()

    @pyqtProperty(str, notify=appAutoUpdateChanged)
    def appAutoUpdateInterval(self): return self._core.appAutoUpdateInterval

    @appAutoUpdateInterval.setter
    def appAutoUpdateInterval(self, value): self._core.appAutoUpdateInterval = value; self.appAutoUpdateChanged.emit()

    @pyqtProperty(bool, notify=severeOnlyChanged)
    def severeOnly(self): return self._core.severeOnly

    @severeOnly.setter
    def severeOnly(self, value): self._core.severeOnly = value; self.severeOnlyChanged.emit()

    @pyqtProperty(bool, notify=autoStageUpdatesChanged)
    def autoStageUpdates(self): return self._core.autoStageUpdates

    @autoStageUpdates.setter
    def autoStageUpdates(self, value): self._core.autoStageUpdates = value; self.autoStageUpdatesChanged.emit()

    @pyqtProperty(str, notify=lastCheckTimeChanged)
    def lastCheckTime(self): return self._core.lastCheckTime

    @pyqtSlot()
    def refreshSystemAutoUpdateStatus(self):
        self.systemAutoUpdateChanged.emit()  # Notify checking
        threading.Thread(
            target=self._refresh_system_auto_update_sync, daemon=True
        ).start()

    def _refresh_system_auto_update_sync(self):
        self._core.refreshSystemAutoUpdateStatus()
        self.systemAutoUpdateChanged.emit()  # Notify done

    @pyqtSlot(bool)
    def toggleSystemAutoUpdate(self, enable):
        self.systemAutoUpdateChanged.emit()  # Notify applying
        threading.Thread(
            target=self._toggle_system_auto_update_sync, args=(enable,), daemon=True
        ).start()

    def _toggle_system_auto_update_sync(self, enable):
        self._core.toggleSystemAutoUpdate(enable)
        self.systemAutoUpdateChanged.emit()  # Notify done

    @pyqtSlot()
    def checkForUpdatesNow(self):
        import datetime
        self._core.lastCheckTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lastCheckTimeChanged.emit()
        if self._backend is not None:
            self._backend.checkForUpdates()

    @pyqtSlot(str, str, bool)
    def sendDesktopNotification(self, title, message, isStagedUpdate=False):
        if not self._core.enableNotifications:
            return
        if isStagedUpdate and not self._core.notifyOnStagedUpdate:
            return
        try:
            from gi.repository import Gio, GLib
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            bus.call_sync(
                "org.freedesktop.Notifications",
                "/org/freedesktop/Notifications",
                "org.freedesktop.Notifications",
                "Notify",
                GLib.Variant("(susssasa{sv}i)", (
                    "Atomic Basejump", 0, "io.github.joshuaroman.AtomicBasejump",
                    title, message, [], {}, -1,
                )),
                GLib.VariantType.new("(u)"), Gio.DBusCallFlags.NONE, 5000, None,
            )
        except Exception:
            import subprocess, os
            cmd = ['notify-send', title, message]
            if os.path.exists('/.flatpak-info'):
                cmd = ['flatpak-spawn', '--host'] + cmd
            subprocess.run(cmd)

from basejump.core.overlays import OverlayService

class OverlayServiceModel(QObject):
    setsChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._core = OverlayService()

    @pyqtProperty('QVariantList', notify=setsChanged)
    def sets(self):
        return list(self._core.sets)

    # QML pages use overlaySets (historical name); keep as alias of sets.
    @pyqtProperty('QVariantList', notify=setsChanged)
    def overlaySets(self):
        return list(self._core.sets)

    @pyqtSlot(str, result='QVariantMap')
    def getOverlaySet(self, id):
        return self._core.getOverlaySet(id)

    @pyqtSlot(str, str, 'QVariantList', 'QVariantList', 'QVariantList', result=str)
    def createOverlaySet(self, name, description, layeredPackages, localPackages, removedPackages):
        ret = self._core.createOverlaySet(name, description, layeredPackages, localPackages, removedPackages)
        self.setsChanged.emit()
        return ret

    @pyqtSlot(str, str, str, 'QVariantList', 'QVariantList', 'QVariantList', result=bool)
    def updateOverlaySet(self, id, name, description, layeredPackages, localPackages, removedPackages):
        ret = self._core.updateOverlaySet(id, name, description, layeredPackages, localPackages, removedPackages)
        self.setsChanged.emit()
        return ret

    @pyqtSlot(str, result=bool)
    def deleteOverlaySet(self, id):
        ret = self._core.deleteOverlaySet(id)
        self.setsChanged.emit()
        return ret

    @pyqtSlot(result=str)
    def exportJson(self):
        return self._core.exportJson()

    @pyqtSlot(str, result=bool)
    def importJson(self, jsonString):
        ret = self._core.importJson(jsonString)
        if ret:
            self.setsChanged.emit()
        return ret
