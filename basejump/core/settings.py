import os
import subprocess

import json
from pathlib import Path

class SettingsManager:
    def __init__(self):
        self._config_path = Path.home() / '.config' / 'atomicbasejump' / 'settings.json'
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = {
            "showTrayIcon": True,
            "enableNotifications": True,
            "notifyOnStagedUpdate": False,
            "appAutoUpdateEnabled": True,
            "appAutoUpdateInterval": "daily",
            "severeOnly": False,
            "autoStageUpdates": False,
            "lastCheckTime": "Never",
            "uiTheme": "Auto"
        }
        self.load()
        self.systemAutoUpdateEnabled = False
        self.systemAutoUpdateStatus = "Checking..."
        self.systemAutoUpdateChecking = False

    def load(self):
        if self._config_path.exists():
            try:
                with open(self._config_path, 'r') as f:
                    self._data.update(json.load(f))
            except (OSError, ValueError, TypeError):
                pass

    def save(self):
        try:
            with open(self._config_path, 'w') as f:
                json.dump(self._data, f)
        except OSError:
            pass

    @property
    def showTrayIcon(self): return self._data["showTrayIcon"]
    @showTrayIcon.setter
    def showTrayIcon(self, v): self._data["showTrayIcon"] = v; self.save()

    @property
    def enableNotifications(self): return self._data["enableNotifications"]
    @enableNotifications.setter
    def enableNotifications(self, v): self._data["enableNotifications"] = v; self.save()

    @property
    def notifyOnStagedUpdate(self): return self._data["notifyOnStagedUpdate"]
    @notifyOnStagedUpdate.setter
    def notifyOnStagedUpdate(self, v): self._data["notifyOnStagedUpdate"] = v; self.save()

    @property
    def appAutoUpdateEnabled(self): return self._data["appAutoUpdateEnabled"]
    @appAutoUpdateEnabled.setter
    def appAutoUpdateEnabled(self, v): self._data["appAutoUpdateEnabled"] = v; self.save()

    @property
    def appAutoUpdateInterval(self): return self._data["appAutoUpdateInterval"]
    @appAutoUpdateInterval.setter
    def appAutoUpdateInterval(self, v): self._data["appAutoUpdateInterval"] = v; self.save()

    @property
    def severeOnly(self): return self._data["severeOnly"]
    @severeOnly.setter
    def severeOnly(self, v): self._data["severeOnly"] = v; self.save()

    @property
    def autoStageUpdates(self): return self._data["autoStageUpdates"]
    @autoStageUpdates.setter
    def autoStageUpdates(self, v): 
        self._data["autoStageUpdates"] = v
        self.save()
        if v and self.systemAutoUpdateEnabled:
            self.toggleSystemAutoUpdate(False)

    @property
    def lastCheckTime(self): return self._data["lastCheckTime"]
    @lastCheckTime.setter
    def lastCheckTime(self, v): self._data["lastCheckTime"] = v; self.save()

    @property
    def uiTheme(self): return self._data["uiTheme"]
    @uiTheme.setter
    def uiTheme(self, v): self._data["uiTheme"] = v; self.save()

    def refreshSystemAutoUpdateStatus(self):
        self.systemAutoUpdateChecking = True
        cmd = ['systemctl', 'is-enabled', 'rpm-ostreed-automatic.timer']
        if os.path.exists('/.flatpak-info'):
            cmd = ['flatpak-spawn', '--host'] + cmd
            
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stdout.strip()
            
            if result.returncode == 0 and "enabled" in output:
                self.systemAutoUpdateEnabled = True
                self.systemAutoUpdateStatus = "Active (rpm-ostreed-automatic.timer enabled)"
            elif "disabled" in output:
                self.systemAutoUpdateEnabled = False
                self.systemAutoUpdateStatus = "Disabled (rpm-ostreed-automatic.timer inactive)"
            else:
                self.systemAutoUpdateEnabled = False
                out_str = output if output else "disabled"
                self.systemAutoUpdateStatus = f"Inactive / Unit not found ({out_str})"
        except Exception as e:
            self.systemAutoUpdateEnabled = False
            self.systemAutoUpdateStatus = f"Error checking status: {str(e)}"
            
        self.systemAutoUpdateChecking = False

    def toggleSystemAutoUpdate(self, enable):
        if enable and self.autoStageUpdates:
            self.autoStageUpdates = False

        cmd_action = 'enable' if enable else 'disable'
        cmd = ['systemctl', f'{cmd_action}', '--now', 'rpm-ostreed-automatic.timer']
        if os.path.exists('/.flatpak-info'):
            cmd = ['flatpak-spawn', '--host', 'pkexec'] + cmd
        else:
            cmd = ['pkexec'] + cmd
            
        try:
            subprocess.run(cmd, capture_output=True, text=True)
        except Exception:
            pass
        self.refreshSystemAutoUpdateStatus()
