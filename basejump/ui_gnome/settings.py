import datetime
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
import threading


class SettingsPage(Gtk.Box):
    def __init__(self, backend, settingsManager):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.backend = backend
        self.settings = settingsManager

        self.toolbar = Adw.ToolbarView()
        self.header = Adw.HeaderBar()
        self.header.set_show_title(True)
        self.title_widget = Adw.WindowTitle(title="Settings")
        self.header.set_title_widget(self.title_widget)
        self.toolbar.add_top_bar(self.header)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.content = Adw.PreferencesPage()

        appearance_grp = Adw.PreferencesGroup(title="Appearance")

        theme_row = Adw.ComboRow(
            title="User Interface Theme",
            subtitle="Choose between native KDE or GNOME visual styles, or Auto",
        )
        model = Gtk.StringList()
        model.append("Auto")
        model.append("KDE")
        model.append("GNOME")
        theme_row.set_model(model)

        current_theme = self.settings.uiTheme
        if current_theme == "KDE":
            theme_row.set_selected(1)
        elif current_theme == "GNOME":
            theme_row.set_selected(2)
        else:
            theme_row.set_selected(0)

        theme_row.connect("notify::selected-item", self.on_theme_changed)
        appearance_grp.add(theme_row)

        self.restart_banner = Adw.Banner(
            title="A restart of the application is required to apply the theme change."
        )
        self.restart_banner.set_revealed(False)
        appearance_grp.add(self.restart_banner)

        notif_grp = Adw.PreferencesGroup(title="Desktop Notifications")

        self.notif_switch = Gtk.Switch()
        self.notif_switch.set_valign(Gtk.Align.CENTER)
        self.notif_switch.set_active(self.settings.enableNotifications)
        self.notif_switch.connect(
            "notify::active",
            lambda w, p: setattr(self.settings, "enableNotifications", w.get_active()),
        )
        notif_row = Adw.ActionRow(title="Enable Desktop Notifications")
        notif_row.add_suffix(self.notif_switch)
        notif_grp.add(notif_row)

        self.staged_switch = Gtk.Switch()
        self.staged_switch.set_valign(Gtk.Align.CENTER)
        self.staged_switch.set_active(self.settings.notifyOnStagedUpdate)
        self.staged_switch.connect(
            "notify::active",
            lambda w, p: setattr(self.settings, "notifyOnStagedUpdate", w.get_active()),
        )
        staged_row = Adw.ActionRow(
            title="Notify when an update is staged",
            subtitle="Alert me when an update is downloaded and ready for reboot",
        )
        staged_row.add_suffix(self.staged_switch)
        notif_grp.add(staged_row)

        sys_grp = Adw.PreferencesGroup(
            title="System Updates",
            description="Host rpm-ostreed-automatic.timer and manual update checks",
        )

        self.sys_auto_switch = Gtk.Switch()
        self.sys_auto_switch.set_valign(Gtk.Align.CENTER)
        self.sys_auto_switch.set_active(self.settings.systemAutoUpdateEnabled)
        self.sys_auto_switch.connect("notify::active", self.on_sys_auto_changed)

        self.sys_auto_row = Adw.ActionRow(
            title="Enable System Auto-Updates",
            subtitle=self.settings.systemAutoUpdateStatus,
        )
        self.sys_auto_row.add_suffix(self.sys_auto_switch)
        sys_grp.add(self.sys_auto_row)

        refresh_btn = Gtk.Button(label="Refresh Status")
        refresh_btn.set_valign(Gtk.Align.CENTER)
        refresh_btn.connect("clicked", self.on_refresh_sys_status)
        self.sys_auto_row.add_suffix(refresh_btn)

        self.last_check_row = Adw.ActionRow(
            title="Last Checked",
            subtitle=self.settings.lastCheckTime,
        )
        check_now = Gtk.Button(label="Check for Updates Now")
        check_now.set_valign(Gtk.Align.CENTER)
        check_now.connect("clicked", self.on_check_now)
        self.last_check_row.add_suffix(check_now)
        sys_grp.add(self.last_check_row)

        self.content.add(appearance_grp)
        self.content.add(notif_grp)
        self.content.add(sys_grp)

        self.scroll.set_child(self.content)
        self.toolbar.set_content(self.scroll)
        self.toolbar.set_vexpand(True)
        self.append(self.toolbar)

        threading.Thread(target=self.settings.refreshSystemAutoUpdateStatus, daemon=True).start()
        GLib.timeout_add(1000, self.update_status)

    def on_theme_changed(self, row, param):
        idx = row.get_selected()
        if idx == 0:
            self.settings.uiTheme = "Auto"
        elif idx == 1:
            self.settings.uiTheme = "KDE"
        elif idx == 2:
            self.settings.uiTheme = "GNOME"
        self.restart_banner.set_revealed(True)

    def on_sys_auto_changed(self, switch, param):
        # update_status() syncs the switch to the model every second; set_active()
        # then emits notify::active. Only treat a real user change (switch state
        # differing from the model) as a toggle request, never a programmatic sync.
        if switch.get_active() == self.settings.systemAutoUpdateEnabled:
            return
        enable = switch.get_active()
        self.settings.systemAutoUpdateChecking = True
        self.sys_auto_row.set_subtitle("Applying...")

        def work():
            self.settings.toggleSystemAutoUpdate(enable)
            self.settings.systemAutoUpdateChecking = False

        threading.Thread(target=work, daemon=True).start()

    def on_refresh_sys_status(self, _btn):
        threading.Thread(target=self.settings.refreshSystemAutoUpdateStatus, daemon=True).start()

    def on_check_now(self, _btn):
        self.settings.lastCheckTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_check_row.set_subtitle(self.settings.lastCheckTime)
        self.backend.checkForUpdates()

    def update_status(self):
        self.sys_auto_switch.set_active(self.settings.systemAutoUpdateEnabled)
        self.sys_auto_row.set_subtitle(self.settings.systemAutoUpdateStatus)
        self.last_check_row.set_subtitle(self.settings.lastCheckTime)
        return GLib.SOURCE_CONTINUE
