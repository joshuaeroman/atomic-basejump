import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio


class OverviewPage(Gtk.Box):
    def __init__(self, backend, overlay_service=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.backend = backend
        self.overlay_service = overlay_service
        self.plasma_repair_dismissed = False

        self.toolbar = Adw.ToolbarView()
        self.header = Adw.HeaderBar()
        self.header.set_show_title(True)
        self.title_widget = Adw.WindowTitle(title="Deployments")
        self.header.set_title_widget(self.title_widget)
        self.toolbar.add_top_bar(self.header)

        self.refresh_btn = Gtk.Button(tooltip_text="Refresh")
        self.refresh_btn.set_child(Adw.ButtonContent(icon_name="view-refresh-symbolic"))
        self.refresh_btn.connect("clicked", lambda x: self.backend.refreshStatus())
        self.header.pack_end(self.refresh_btn)

        self.check_btn = Gtk.Button(tooltip_text="Check for Updates")
        self.check_btn.set_child(Adw.ButtonContent(icon_name="emblem-synchronizing-symbolic", label="Check"))
        self.check_btn.connect("clicked", lambda x: self.backend.checkForUpdates())
        self.header.pack_end(self.check_btn)

        self.upgrade_btn = Gtk.Button(tooltip_text="Upgrade System")
        self.upgrade_btn.set_child(Adw.ButtonContent(icon_name="software-update-available-symbolic", label="Upgrade"))
        self.upgrade_btn.connect("clicked", lambda x: self.backend.upgradeSystem())
        self.upgrade_btn.set_visible(False)
        self.header.pack_end(self.upgrade_btn)

        self.reboot_btn = Gtk.Button(tooltip_text="Reboot System")
        self.reboot_btn.set_child(Adw.ButtonContent(icon_name="system-shutdown-symbolic", label="Reboot"))
        self.reboot_btn.add_css_class("suggested-action")
        self.reboot_btn.connect("clicked", lambda x: self.backend.rebootSystem())
        self.reboot_btn.set_visible(False)
        self.header.pack_end(self.reboot_btn)

        self.log_btn = Gtk.Button(tooltip_text="View transaction log")
        self.log_btn.set_child(Adw.ButtonContent(icon_name="utilities-terminal-symbolic", label="Log"))
        self.log_btn.connect("clicked", self.on_view_log)
        self.header.pack_start(self.log_btn)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.content_box.set_margin_top(24)
        self.content_box.set_margin_bottom(24)
        self.content_box.set_margin_start(24)
        self.content_box.set_margin_end(24)
        self.content_box.set_halign(Gtk.Align.CENTER)
        self.content_box.set_size_request(600, -1)

        self.status_banner = Adw.Banner()
        self.content_box.append(self.status_banner)

        self.plasma_repair_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.plasma_repair_banner = Adw.Banner(
            title=(
                "Repair pending Plasma login: a Plasma deployment is staged while you are "
                "on a non-Plasma system. Without repairing login accounts, the next Plasma "
                "boot may show a black screen."
            )
        )
        self.plasma_repair_banner.set_vexpand(False)
        self.plasma_repair_banner.set_button_label("Repair")
        self.plasma_repair_banner.connect(
            "button-clicked", lambda x: self.backend.prepPlasmaLoginAccounts(True)
        )
        self.plasma_repair_box.append(self.plasma_repair_banner)
        dismiss_btn = Gtk.Button(
            icon_name="window-close-symbolic", valign=Gtk.Align.CENTER
        )
        dismiss_btn.add_css_class("flat")
        dismiss_btn.set_tooltip_text("Dismiss")
        dismiss_btn.connect(
            "clicked", lambda x: setattr(self, "plasma_repair_dismissed", True)
        )
        self.plasma_repair_box.append(dismiss_btn)
        self.content_box.append(self.plasma_repair_box)

        self.progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.progress_box.set_visible(False)
        self.progress_label = Gtk.Label(label="", xalign=0)
        self.progress_label.add_css_class("heading")
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_pulse_step(0.08)
        self.progress_box.append(self.progress_label)
        self.progress_box.append(self.progress_bar)
        self.content_box.append(self.progress_box)

        self.deployments_list = Gtk.ListBox()
        self.deployments_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.deployments_list.set_css_classes(["boxed-list"])
        self.content_box.append(self.deployments_list)

        self.scroll.set_child(self.content_box)
        self.toolbar.set_content(self.scroll)
        self.toolbar.set_vexpand(True)
        self.append(self.toolbar)

        GLib.timeout_add(500, self.update_ui)
        self.last_status = None
        self.last_deps = []

    def get_parent_window(self):
        widget = self
        while widget.get_parent():
            widget = widget.get_parent()
        return widget

    def create_package_flow(self, packages, color_class=None):
        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_max_children_per_line(10)
        flow.set_column_spacing(6)
        flow.set_row_spacing(6)

        if not packages:
            lbl = Gtk.Label(label="None")
            lbl.add_css_class("dim-label")
            lbl.set_halign(Gtk.Align.START)
            return lbl

        for pkg in packages:
            name = pkg.split('/')[-1] if '/' in pkg else pkg
            lbl = Gtk.Label(label=name)
            lbl.add_css_class("numeric")

            box = Gtk.Box()
            box.add_css_class("card")
            if color_class:
                box.add_css_class(color_class)
            box.set_margin_top(2)
            box.set_margin_bottom(2)
            box.set_margin_start(2)
            box.set_margin_end(2)
            lbl.set_margin_start(6)
            lbl.set_margin_end(6)
            lbl.set_margin_top(2)
            lbl.set_margin_bottom(2)
            box.append(lbl)
            flow.insert(box, -1)

        return flow

    def on_view_log(self, _btn):
        dialog = Adw.Dialog()
        dialog.set_title("Transaction Console Output")
        dialog.set_content_width(640)
        dialog.set_content_height(480)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        close_btn = Gtk.Button(label="Close")
        close_btn.connect("clicked", lambda x: dialog.close())
        header.pack_end(close_btn)

        clear_btn = Gtk.Button(label="Clear")
        clear_btn.connect("clicked", lambda x: self._clear_log(buffer, dialog))
        header.pack_start(clear_btn)
        toolbar.add_top_bar(header)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_monospace(True)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        buffer = text_view.get_buffer()
        log = self.backend.transactionLog or "No console output recorded."
        if self.backend.lastError:
            log = log + "\n\nError:\n" + self.backend.lastError
        buffer.set_text(log)
        scrolled.set_child(text_view)
        toolbar.set_content(scrolled)
        dialog.set_child(toolbar)

        if getattr(self, "_log_update_id", None) is not None:
            GLib.source_remove(self._log_update_id)
            self._log_update_id = None
        self._log_update_id = GLib.timeout_add(500, self._update_log_buffer, buffer, dialog)
        dialog.connect("closed", self._on_log_dialog_closed)
        dialog.present(self.get_parent_window())

    def _update_log_buffer(self, buffer, dialog):
        log = self.backend.transactionLog or "No console output recorded."
        if self.backend.lastError:
            log = log + "\n\nError:\n" + self.backend.lastError
        current = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        if current != log:
            buffer.set_text(log)
        return GLib.SOURCE_CONTINUE if self.backend.transactionInProgress else GLib.SOURCE_REMOVE

    def _on_log_dialog_closed(self, dialog):
        if getattr(self, "_log_update_id", None) is not None:
            GLib.source_remove(self._log_update_id)
            self._log_update_id = None

    def _clear_log(self, buffer, dialog):
        if hasattr(self.backend, "clearTransactionLog"):
            self.backend.clearTransactionLog()
        else:
            self.backend.transactionLog = ""
            self.backend.statusBannerMessage = ""
            self.backend.lastError = ""
        buffer.set_text("No console output recorded.")

    def on_save_overlay_set(self, _btn, dep):
        if not self.overlay_service:
            return
        dialog = Adw.Dialog()
        dialog.set_title("Save as Overlay Set")
        dialog.set_content_width(420)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda x: dialog.close())
        header.pack_start(cancel)
        save = Gtk.Button(label="Save")
        save.add_css_class("suggested-action")
        header.pack_end(save)
        toolbar.add_top_bar(header)

        page = Adw.PreferencesPage()
        grp = Adw.PreferencesGroup()
        name_row = Adw.EntryRow(title="Profile Name")
        name_row.set_text((dep.get("osname") or "Deployment") + " Overlay Set")
        desc_row = Adw.EntryRow(title="Description")
        desc_row.set_text("Saved from deployment")
        grp.add(name_row)
        grp.add(desc_row)
        page.add(grp)
        toolbar.set_content(page)
        dialog.set_child(toolbar)

        def do_save(_b):
            self.overlay_service.createOverlaySet(
                name_row.get_text(),
                desc_row.get_text(),
                list(dep.get("requested-packages") or []),
                list(dep.get("requested-local-packages") or []),
                list(dep.get("requested-base-removals") or []),
            )
            dialog.close()

        save.connect("clicked", do_save)
        dialog.present(self.get_parent_window())

    def on_override_overlays(self, _btn):
        if not self.overlay_service:
            return
        dialog = Adw.Dialog()
        dialog.set_title("Override System Overlay Set")
        dialog.set_content_width(480)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda x: dialog.close())
        header.pack_start(cancel)
        apply_btn = Gtk.Button(label="Apply to System")
        apply_btn.add_css_class("suggested-action")
        header.pack_end(apply_btn)
        toolbar.add_top_bar(header)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        box.set_margin_start(18)
        box.set_margin_end(18)

        lbl = Gtk.Label(
            label=(
                "Select an Overlay Set to apply package modifications, or remove all "
                "overlays to start fresh:"
            ),
            wrap=True,
            xalign=0,
        )
        box.append(lbl)

        choices = list(self.overlay_service.sets)
        string_list = Gtk.StringList()
        for s in choices:
            string_list.append(s.get("name") or "Unnamed")
        string_list.append("Remove all overlays (start fresh)")

        combo = Adw.ComboRow(title="Overlay Set")
        combo.set_model(string_list)
        if string_list.get_n_items() > 0:
            combo.set_selected(0)
        box.append(combo)

        preview = Gtk.Label(label="", wrap=True, xalign=0)
        preview.add_css_class("dim-label")
        box.append(preview)

        def update_preview(*_a):
            idx = combo.get_selected()
            if idx == Gtk.INVALID_LIST_POSITION:
                preview.set_text("")
                return
            if idx >= len(choices):
                preview.set_text(
                    "This runs rpm-ostree reset: all layered packages, local packages, "
                    "and package overrides will be removed."
                )
                apply_btn.set_label("Remove All Overlays")
                return
            s = choices[idx]
            parts = []
            if s.get("layeredPackages"):
                parts.append("Layered: " + ", ".join(s["layeredPackages"]))
            if s.get("localPackages"):
                parts.append("Local: " + ", ".join(s["localPackages"]))
            if s.get("removedPackages"):
                parts.append("Removed: " + ", ".join(s["removedPackages"]))
            preview.set_text("\n".join(parts) if parts else "(empty set)")
            apply_btn.set_label("Apply to System")

        combo.connect("notify::selected", update_preview)
        update_preview()

        def do_apply(_b):
            idx = combo.get_selected()
            if idx == Gtk.INVALID_LIST_POSITION:
                return
            if idx >= len(choices):
                self.backend.resetOverlays()
            else:
                s = choices[idx]
                self.backend.applyOverlaySet(
                    s.get("layeredPackages") or [],
                    s.get("localPackages") or [],
                    s.get("removedPackages") or [],
                )
            dialog.close()

        apply_btn.connect("clicked", do_apply)
        toolbar.set_content(box)
        dialog.set_child(toolbar)
        dialog.present(self.get_parent_window())

    def update_ui(self):
        if self.backend.statusBannerMessage:
            self.status_banner.set_title(self.backend.statusBannerMessage)
            self.status_banner.set_revealed(True)
        else:
            self.status_banner.set_revealed(False)

        if getattr(self.backend, "plasmaLoginRepairAvailable", False) and not self.plasma_repair_dismissed:
            self.plasma_repair_banner.set_revealed(True)
            self.plasma_repair_box.set_visible(True)
        else:
            self.plasma_repair_banner.set_revealed(False)
            self.plasma_repair_box.set_visible(False)

        in_progress = self.backend.transactionInProgress
        self.progress_box.set_visible(in_progress)
        if in_progress:
            self.progress_label.set_text(self.backend.currentTask or self.backend.transactionMessage or "Working...")
            pct = max(0, min(100, int(self.backend.transactionProgress or 0)))
            if pct > 0:
                # Native D-Bus transactions report a percentage.
                self.progress_bar.set_fraction(pct / 100.0)
                self.progress_bar.set_text(f"{pct}%")
                self.progress_bar.set_show_text(True)
            else:
                # Sandboxed transactions run through the CLI, which exposes no
                # percentage data; show an indeterminate pulsing bar instead.
                self.progress_bar.set_show_text(False)
                self.progress_bar.pulse()

        self.upgrade_btn.set_visible(self.backend.updateAvailable and not self.backend.rebootRequired)
        self.upgrade_btn.set_sensitive(not in_progress)
        self.reboot_btn.set_visible(self.backend.rebootRequired)
        self.reboot_btn.set_sensitive(not in_progress)
        self.refresh_btn.set_sensitive(not in_progress)
        self.check_btn.set_sensitive(not in_progress)
        self.log_btn.set_sensitive(bool(self.backend.transactionLog) or in_progress)

        current_deps = self.backend.deployments
        if self.last_deps != current_deps:
            self.last_deps = list(current_deps)
            while child := self.deployments_list.get_first_child():
                self.deployments_list.remove(child)

            for i, dep in enumerate(current_deps):
                row = Adw.ExpanderRow()

                ref = dep.get("ref", "")
                version = dep.get("version", "")
                commit = (dep.get("commit") or dep.get("checksum") or "")[:7]

                title = f"{ref}"
                if version:
                    title += f" (Version: {version})"
                row.set_title(title)

                subtitle = f"Commit: {commit}"
                if dep.get("booted"):
                    subtitle += " • Booted"
                if dep.get("staged"):
                    subtitle += " • Staged"
                if dep.get("pinned"):
                    subtitle += " • Pinned"
                row.set_subtitle(subtitle)

                if dep.get("booted"):
                    icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
                    row.add_prefix(icon)
                else:
                    icon = Gtk.Image.new_from_icon_name("drive-harddisk-symbolic")
                    row.add_prefix(icon)

                details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
                details.set_margin_start(12)
                details.set_margin_end(12)
                details.set_margin_top(12)
                details.set_margin_bottom(12)

                lbl = Gtk.Label(label="Layered Packages:")
                lbl.set_halign(Gtk.Align.START)
                lbl.add_css_class("heading")
                details.append(lbl)
                details.append(self.create_package_flow(dep.get("requested-packages", []), "chip-layered"))

                lbl = Gtk.Label(label="Local Packages:")
                lbl.set_halign(Gtk.Align.START)
                lbl.add_css_class("heading")
                details.append(lbl)
                details.append(self.create_package_flow(dep.get("requested-local-packages", []), "chip-local"))

                lbl = Gtk.Label(label="Removed Packages:")
                lbl.set_halign(Gtk.Align.START)
                lbl.add_css_class("heading")
                details.append(lbl)
                details.append(self.create_package_flow(dep.get("requested-base-removals", []), "chip-removed"))

                actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                actions_box.set_halign(Gtk.Align.END)
                actions_box.set_margin_top(12)

                if dep.get("pinned"):
                    unpin_btn = Gtk.Button()
                    unpin_btn.set_child(Adw.ButtonContent(icon_name="view-pin-symbolic", label="Unpin"))
                    unpin_btn.connect("clicked", lambda x, idx=i: self.backend.unpinDeployment(idx))
                    actions_box.append(unpin_btn)
                else:
                    pin_btn = Gtk.Button()
                    pin_btn.set_child(Adw.ButtonContent(icon_name="view-pin-symbolic", label="Pin"))
                    pin_btn.connect("clicked", lambda x, idx=i: self.backend.pinDeployment(idx))
                    actions_box.append(pin_btn)

                if not dep.get("booted") and not dep.get("staged"):
                    rollback_btn = Gtk.Button()
                    rollback_btn.set_child(Adw.ButtonContent(icon_name="edit-undo-symbolic", label="Rollback"))
                    rollback_btn.connect("clicked", lambda x: self.backend.rollbackSystem())
                    actions_box.append(rollback_btn)

                save_btn = Gtk.Button()
                save_btn.set_child(Adw.ButtonContent(icon_name="document-save-symbolic", label="Save as Overlay Set"))
                save_btn.connect("clicked", self.on_save_overlay_set, dep)

                override_btn = Gtk.Button()
                override_btn.set_child(Adw.ButtonContent(icon_name="document-edit-symbolic", label="Override Overlays"))
                override_btn.connect("clicked", self.on_override_overlays)

                actions_box.append(save_btn)
                actions_box.append(override_btn)
                details.append(actions_box)

                row.add_row(details)
                self.deployments_list.append(row)

        return GLib.SOURCE_CONTINUE
