import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio
import threading


class OverlaySetDialog(Adw.Window):
    def __init__(self, parent, backend, overlayService, set_data=None):
        super().__init__(
            transient_for=parent,
            modal=True,
            title="Edit Overlay Set" if set_data else "Create Overlay Set",
        )
        self.set_default_size(500, 600)
        self.backend = backend
        self.overlayService = overlayService
        self.set_data = set_data

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda x: self.close())
        header.pack_start(cancel_btn)

        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self.on_save)
        header.pack_end(save_btn)

        page = Adw.PreferencesPage()

        grp_info = Adw.PreferencesGroup(title="General Information")
        self.name_entry = Adw.EntryRow(title="Name")
        self.desc_entry = Adw.EntryRow(title="Description")
        grp_info.add(self.name_entry)
        grp_info.add(self.desc_entry)
        page.add(grp_info)

        grp_pkgs = Adw.PreferencesGroup(
            title="Packages", description="Comma-separated lists of packages"
        )

        self.layered_row = Adw.ActionRow(title="Layered")
        self.layered_entry = Gtk.Entry(hexpand=True, valign=Gtk.Align.CENTER)
        self.layered_entry.set_placeholder_text("Comma-separated packages")

        layered_completion = Gtk.EntryCompletion()
        self.layered_model = Gtk.ListStore(str)
        layered_completion.set_model(self.layered_model)
        layered_completion.set_text_column(0)
        layered_completion.set_match_func(self.comma_match_func)
        layered_completion.connect("match-selected", self.on_layered_match_selected)
        self.layered_entry.set_completion(layered_completion)
        self.layered_entry.connect("changed", self.on_layered_changed)

        self.search_term = ""
        self._search_timeout_id = None

        self.layered_row.add_suffix(self.layered_entry)
        grp_pkgs.add(self.layered_row)

        self.local_row = Adw.ActionRow(title="Local RPMs")
        box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6,
            hexpand=True,
            valign=Gtk.Align.CENTER,
        )
        self.local_entry = Gtk.Entry(hexpand=True)
        self.local_entry.set_placeholder_text("Comma-separated paths")
        self.local_browse_btn = Gtk.Button(icon_name="document-open-symbolic")
        self.local_browse_btn.connect("clicked", self.on_browse_local)
        box.append(self.local_entry)
        box.append(self.local_browse_btn)
        self.local_row.add_suffix(box)
        grp_pkgs.add(self.local_row)

        self.removed_row = Adw.ActionRow(title="Removed Base")
        self.removed_entry = Gtk.Entry(hexpand=True, valign=Gtk.Align.CENTER)
        self.removed_entry.set_placeholder_text("Comma-separated packages")

        removed_completion = Gtk.EntryCompletion()
        self.removed_model = Gtk.ListStore(str)
        removed_completion.set_model(self.removed_model)
        removed_completion.set_text_column(0)
        removed_completion.set_match_func(self.comma_match_func)
        removed_completion.connect("match-selected", self.on_removed_match_selected)
        self.removed_entry.set_completion(removed_completion)

        self.removed_row.add_suffix(self.removed_entry)
        grp_pkgs.add(self.removed_row)

        page.add(grp_pkgs)

        if set_data:
            self.name_entry.set_text(set_data.get("name", ""))
            self.desc_entry.set_text(set_data.get("description", ""))
            self.layered_entry.set_text(", ".join(set_data.get("layeredPackages", [])))
            self.local_entry.set_text(", ".join(set_data.get("localPackages", [])))
            self.removed_entry.set_text(", ".join(set_data.get("removedPackages", [])))

        scroll = Gtk.ScrolledWindow()
        scroll.set_child(page)
        toolbar_view.set_content(scroll)
        self.set_content(toolbar_view)

        GLib.idle_add(self.populate_completions)

    def populate_completions(self):
        pkgs = self.backend.getDeploymentPackages()
        for p in pkgs:
            self.layered_model.append([p])
            self.removed_model.append([p])

    def comma_match_func(self, completion, key, iter):
        entry = completion.get_entry()
        if not entry:
            return False
        text = entry.get_text()
        term = text.split(",")[-1].strip().lower()
        if not term:
            return False
        model = completion.get_model()
        item = model.get_value(iter, 0).lower()
        return term in item

    def on_layered_match_selected(self, completion, model, iter):
        item = model.get_value(iter, 0)
        current = self.layered_entry.get_text()
        parts = current.split(",")
        parts[-1] = " " + item if len(parts) > 1 else item
        self.layered_entry.set_text(",".join(parts) + ", ")
        self.layered_entry.set_position(-1)
        return True

    def on_removed_match_selected(self, completion, model, iter):
        item = model.get_value(iter, 0)
        current = self.removed_entry.get_text()
        parts = current.split(",")
        parts[-1] = " " + item if len(parts) > 1 else item
        self.removed_entry.set_text(",".join(parts) + ", ")
        self.removed_entry.set_position(-1)
        return True

    def on_layered_changed(self, entry):
        text = entry.get_text()
        term = text.split(",")[-1].strip()
        if len(term) >= 2 and term != self.search_term:
            if self._search_timeout_id is not None:
                GLib.source_remove(self._search_timeout_id)
            self._search_timeout_id = GLib.timeout_add(300, self._on_search_timeout, term)

    def _on_search_timeout(self, term):
        self._search_timeout_id = None
        if term != self.search_term:
            self.search_term = term
            threading.Thread(target=self._run_search, args=(term,), daemon=True).start()
        return GLib.SOURCE_REMOVE

    def _run_search(self, term):
        res = self.backend.searchPackages(term)
        GLib.idle_add(self._update_layered_model, res, term)

    def _update_layered_model(self, res, term):
        if self.search_term != term:
            return
        self.layered_model.clear()
        for p in res:
            self.layered_model.append([p["name"]])

    def on_browse_local(self, btn):
        dialog = Gtk.FileDialog(title="Select Local RPM")
        dialog.open(self, None, self._on_browse_cb)

    def _on_browse_cb(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                current = self.local_entry.get_text()
                if current:
                    self.local_entry.set_text(current + ", " + file.get_path())
                else:
                    self.local_entry.set_text(file.get_path())
        except GLib.Error:
            pass

    def on_save(self, btn):
        name = self.name_entry.get_text()
        desc = self.desc_entry.get_text()
        layered = [x.strip() for x in self.layered_entry.get_text().split(",") if x.strip()]
        local = [x.strip() for x in self.local_entry.get_text().split(",") if x.strip()]
        removed = [x.strip() for x in self.removed_entry.get_text().split(",") if x.strip()]

        if self.set_data:
            self.overlayService.updateOverlaySet(
                self.set_data["id"], name, desc, layered, local, removed
            )
        else:
            self.overlayService.createOverlaySet(name, desc, layered, local, removed)

        self.close()


class OverlaySetsPage(Gtk.Box):
    def __init__(self, backend, overlayService):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.backend = backend
        self.overlayService = overlayService
        self.filter_text = ""

        self.toolbar = Adw.ToolbarView()
        self.header = Adw.HeaderBar()
        self.header.set_show_title(True)
        self.title_widget = Adw.WindowTitle(title="Overlay Sets")
        self.header.set_title_widget(self.title_widget)
        self.toolbar.add_top_bar(self.header)

        self.add_btn = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Create Overlay Set")
        self.add_btn.connect("clicked", self.on_create_clicked)
        self.header.pack_end(self.add_btn)

        menu = Gio.Menu.new()
        menu.append("Export to JSON", "app.export_overlays")
        menu.append("Import from JSON", "app.import_overlays")
        self.menu_btn = Gtk.MenuButton(icon_name="view-more-symbolic", tooltip_text="More Options")
        self.menu_btn.set_menu_model(menu)
        self.header.pack_end(self.menu_btn)

        app = Gio.Application.get_default()
        if app and not app.lookup_action("export_overlays"):
            act_exp = Gio.SimpleAction.new("export_overlays", None)
            act_exp.connect("activate", self.on_export)
            app.add_action(act_exp)

            act_imp = Gio.SimpleAction.new("import_overlays", None)
            act_imp.connect("activate", self.on_import)
            app.add_action(act_imp)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.content_box.set_margin_top(24)
        self.content_box.set_margin_bottom(24)
        self.content_box.set_margin_start(24)
        self.content_box.set_margin_end(24)
        self.content_box.set_halign(Gtk.Align.CENTER)
        self.content_box.set_size_request(600, -1)

        self.filter_entry = Gtk.SearchEntry()
        self.filter_entry.set_placeholder_text("Filter overlay sets...")
        self.filter_entry.connect("search-changed", self.on_filter_changed)
        self.content_box.append(self.filter_entry)

        self.status_page = Adw.StatusPage()
        self.status_page.set_title("Overlay Sets")
        self.status_page.set_description(
            "Manage groups of layered packages, local RPMs, and removed base packages."
        )
        self.status_page.set_icon_name("emblem-system-symbolic")
        self.content_box.append(self.status_page)

        self.sets_list = Gtk.ListBox()
        self.sets_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.sets_list.set_css_classes(["boxed-list"])
        self.content_box.append(self.sets_list)

        self.scroll.set_child(self.content_box)
        self.toolbar.set_content(self.scroll)
        self.toolbar.set_vexpand(True)
        self.append(self.toolbar)

        GLib.timeout_add(1000, self.update_ui)
        self.last_sets = None
        self.last_filter = None

    def get_parent_window(self):
        widget = self
        while widget.get_parent():
            widget = widget.get_parent()
        return widget

    def on_filter_changed(self, entry):
        self.filter_text = (entry.get_text() or "").strip().lower()
        self.last_sets = None  # force rebuild

    def on_create_clicked(self, btn):
        dialog = OverlaySetDialog(self.get_parent_window(), self.backend, self.overlayService)
        dialog.present()

    def on_edit_clicked(self, btn, set_data):
        dialog = OverlaySetDialog(
            self.get_parent_window(), self.backend, self.overlayService, set_data
        )
        dialog.present()

    def on_delete_clicked(self, btn, set_id):
        self.overlayService.deleteOverlaySet(set_id)
        self.last_sets = None

    def on_duplicate_clicked(self, btn, set_data):
        self.overlayService.createOverlaySet(
            (set_data.get("name") or "Set") + " (Copy)",
            set_data.get("description") or "",
            list(set_data.get("layeredPackages") or []),
            list(set_data.get("localPackages") or []),
            list(set_data.get("removedPackages") or []),
        )
        self.last_sets = None

    def on_export(self, action, param):
        dialog = Gtk.FileDialog(title="Export Overlay Sets")
        dialog.save(self.get_parent_window(), None, self._on_export_cb)

    def _on_export_cb(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if file:
                data = self.overlayService.exportJson()
                with open(file.get_path(), "w") as f:
                    f.write(data)
        except GLib.Error:
            pass

    def on_import(self, action, param):
        dialog = Gtk.FileDialog(title="Import Overlay Sets")
        dialog.open(self.get_parent_window(), None, self._on_import_cb)

    def _on_import_cb(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                with open(file.get_path(), "r") as f:
                    data = f.read()
                self.overlayService.importJson(data)
                self.last_sets = None
        except GLib.Error:
            pass

    def update_ui(self):
        current_sets = list(self.overlayService.sets)
        if self.last_sets == current_sets and self.last_filter == self.filter_text:
            return GLib.SOURCE_CONTINUE

        self.last_sets = current_sets
        self.last_filter = self.filter_text

        while child := self.sets_list.get_first_child():
            self.sets_list.remove(child)

        filtered = current_sets
        if self.filter_text:
            filtered = [
                s
                for s in current_sets
                if self.filter_text in (s.get("name") or "").lower()
                or self.filter_text in (s.get("description") or "").lower()
            ]

        for s in filtered:
            row = Adw.ActionRow()
            row.set_title(s.get("name", "Unnamed Set"))
            row.set_subtitle(s.get("description", ""))

            dup_btn = Gtk.Button(icon_name="edit-copy-symbolic", valign=Gtk.Align.CENTER)
            dup_btn.add_css_class("flat")
            dup_btn.set_tooltip_text("Duplicate")
            dup_btn.connect("clicked", self.on_duplicate_clicked, s)
            row.add_suffix(dup_btn)

            edit_btn = Gtk.Button(icon_name="document-edit-symbolic", valign=Gtk.Align.CENTER)
            edit_btn.add_css_class("flat")
            edit_btn.connect("clicked", self.on_edit_clicked, s)
            row.add_suffix(edit_btn)

            del_btn = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
            del_btn.add_css_class("flat")
            del_btn.add_css_class("destructive-action")
            del_btn.connect("clicked", self.on_delete_clicked, s["id"])
            row.add_suffix(del_btn)

            apply_btn = Gtk.Button(label="Apply", valign=Gtk.Align.CENTER)
            apply_btn.connect(
                "clicked",
                lambda x, sid=s["id"]: self.backend.applyOverlaySet(
                    self.overlayService.getOverlaySet(sid).get("layeredPackages", []),
                    self.overlayService.getOverlaySet(sid).get("localPackages", []),
                    self.overlayService.getOverlaySet(sid).get("removedPackages", []),
                ),
            )
            row.add_suffix(apply_btn)

            self.sets_list.append(row)

        self.status_page.set_visible(len(filtered) == 0)

        return GLib.SOURCE_CONTINUE
