import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib


class ImageBrowserPage(Gtk.Box):
    def __init__(self, backend, imageRegistry, overlay_service=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.backend = backend
        self.imageRegistry = imageRegistry
        self.overlay_service = overlay_service
        self.full_ref = ""
        self.types = []
        self.current_source_id = ""
        self.available_streams = []
        self.available_versions = []
        self.use_version_tag = False
        self.selected_overlay_id = ""
        self._applied_booted = False
        self._loading_tags = False

        self.toolbar = Adw.ToolbarView()
        self.header = Adw.HeaderBar()
        self.header.set_show_title(True)
        self.title_widget = Adw.WindowTitle(title="OS Image Browser")
        self.header.set_title_widget(self.title_widget)
        self.toolbar.add_top_bar(self.header)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.content = Adw.PreferencesPage()

        sel_grp = Adw.PreferencesGroup(title="Target Reference Selection")

        self.source_row = Adw.ComboRow(title="Image Source")
        self.source_model = Gtk.StringList()
        self.sources = self.imageRegistry.sources()
        for s in self.sources:
            self.source_model.append(s.get("name", s.get("id")))
        self.source_row.set_model(self.source_model)
        self.source_row.connect("notify::selected-item", self.on_source_changed)
        sel_grp.add(self.source_row)

        self.type_row = Adw.ComboRow(title="Image Variant")
        self.type_model = Gtk.StringList()
        self.type_row.set_model(self.type_model)
        self.type_row.connect("notify::selected-item", self.on_type_changed)
        sel_grp.add(self.type_row)

        self.tag_mode_row = Adw.ComboRow(title="Tag Type")
        self.tag_mode_model = Gtk.StringList.new(["Release Stream", "Specific Version"])
        self.tag_mode_row.set_model(self.tag_mode_model)
        self.tag_mode_row.connect("notify::selected-item", self.on_tag_mode_changed)
        sel_grp.add(self.tag_mode_row)

        self.tag_row = Adw.ComboRow(title="Release Tag")
        self.tag_model = Gtk.StringList()
        self.tag_row.set_model(self.tag_model)
        self.tag_row.connect("notify::selected-item", self.on_tag_changed)
        sel_grp.add(self.tag_row)

        self.build_date_row = Adw.ActionRow(title="Build Date", subtitle="—")
        sel_grp.add(self.build_date_row)

        self.content.add(sel_grp)

        ref_grp = Adw.PreferencesGroup(title="Selected Target Reference")

        self.ref_row = Adw.ActionRow(title="Target Reference", subtitle="Waiting for selection...")
        ref_grp.add(self.ref_row)

        self.signed_switch = Gtk.Switch()
        self.signed_switch.set_valign(Gtk.Align.CENTER)
        self.signed_switch.set_active(True)
        self.signed_switch.connect("notify::active", lambda w, p: self.update_ref())
        self.signed_row = Adw.ActionRow(
            title="Require Signature Verification",
            subtitle="Uses ostree-image-signed when enabled",
        )
        self.signed_row.add_suffix(self.signed_switch)
        ref_grp.add(self.signed_row)

        self.plasma_prep_switch = Gtk.Switch()
        self.plasma_prep_switch.set_valign(Gtk.Align.CENTER)
        self.plasma_prep_switch.set_active(True)
        self.plasma_prep_row = Adw.ActionRow(
            title="Prepare Plasma Login Manager accounts",
            subtitle=(
                "You are switching to a Plasma base. Atomic Basejump will prepare the "
                "Plasma login manager account so the login screen works after reboot."
            ),
        )
        self.plasma_prep_row.add_suffix(self.plasma_prep_switch)
        self.plasma_prep_row.set_visible(False)
        ref_grp.add(self.plasma_prep_row)

        self.overlay_row = Adw.ComboRow(title="Apply Overlay Set")
        self.overlay_model = Gtk.StringList()
        self.overlay_row.set_model(self.overlay_model)
        self.overlay_row.connect("notify::selected-item", self.on_overlay_changed)
        ref_grp.add(self.overlay_row)

        self.rebase_btn = Gtk.Button(label="Rebase to Image")
        self.rebase_btn.set_margin_top(12)
        self.rebase_btn.add_css_class("suggested-action")
        self.rebase_btn.connect("clicked", self.on_rebase_clicked)
        ref_grp.add(self.rebase_btn)

        self.content.add(ref_grp)

        self.scroll.set_child(self.content)
        self.toolbar.set_content(self.scroll)
        self.toolbar.set_vexpand(True)
        self.append(self.toolbar)

        self.refresh_overlay_choices()
        if self.source_row.get_selected() == Gtk.INVALID_LIST_POSITION:
            self.source_row.set_selected(0)
        GLib.idle_add(self.apply_booted_selection)
        GLib.timeout_add(2000, self._periodic_booted_try)

    def get_parent_window(self):
        widget = self
        while widget.get_parent():
            widget = widget.get_parent()
        return widget

    def _periodic_booted_try(self):
        self._booted_try_count = getattr(self, "_booted_try_count", 0) + 1
        if not self._applied_booted:
            self.apply_booted_selection()
        # Stop after 60s: the page keeps its default catalog selection either way.
        return not self._applied_booted and self._booted_try_count < 30

    def refresh_overlay_choices(self):
        self.overlay_model.splice(0, self.overlay_model.get_n_items(), [])
        self._overlay_ids = ["", "__reset_all__"]
        self.overlay_model.append("None (Keep current package layer)")
        self.overlay_model.append("Remove all overlays (start fresh)")
        if self.overlay_service:
            for s in self.overlay_service.sets:
                self._overlay_ids.append(s.get("id") or "")
                self.overlay_model.append(s.get("name") or "Unnamed")
        self.overlay_row.set_selected(0)
        self.selected_overlay_id = ""

    def on_overlay_changed(self, row, _p):
        idx = row.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION or not hasattr(self, "_overlay_ids"):
            self.selected_overlay_id = ""
            return
        if idx < len(self._overlay_ids):
            self.selected_overlay_id = self._overlay_ids[idx]
        else:
            self.selected_overlay_id = ""

    def apply_booted_selection(self):
        if self._applied_booted:
            return False
        booted = self.backend.bootedDeployment or {}
        ref = (
            booted.get("container-image-reference")
            or booted.get("ref")
            or booted.get("origin")
            or ""
        )
        if not ref:
            return False
        sel = self.imageRegistry.resolveBootedSelection(ref)
        if not sel.get("found"):
            self._applied_booted = True
            self.apply_signature_default(ref)
            return False

        src_idx = sel.get("sourceIndex", -1)
        if 0 <= src_idx < len(self.sources):
            self.source_row.set_selected(src_idx)
            # on_source_changed repopulates types
            type_idx = sel.get("typeIndex", 0)
            if 0 <= type_idx < self.type_model.get_n_items():
                self.type_row.set_selected(type_idx)

        tag = sel.get("tag") or ""
        if sel.get("useVersionTag"):
            self.tag_mode_row.set_selected(1)
            self.use_version_tag = True
        else:
            self.tag_mode_row.set_selected(0)
            self.use_version_tag = False
        self._preferred_tag = tag
        self.apply_signature_default(ref)
        self._applied_booted = True
        self.refresh_tags()
        return False

    def apply_signature_default(self, booted_ref=""):
        booted_ref = booted_ref or (
            (self.backend.bootedDeployment or {}).get("container-image-reference")
            or (self.backend.bootedDeployment or {}).get("ref")
            or ""
        )
        type_idx = self.type_row.get_selected()
        supports = False
        if type_idx != Gtk.INVALID_LIST_POSITION and self.types:
            supports = bool(self.types[type_idx].get("supportsSignatureChoice"))
        image_ref = ""
        if type_idx != Gtk.INVALID_LIST_POSITION and self.types:
            image_ref = self.types[type_idx].get("imageRef", "")

        allow_signed = self.imageRegistry.allowsSignedUblueTarget(booted_ref)
        is_ublue = self.imageRegistry.isUblueRef(image_ref)
        if supports or is_ublue:
            self.signed_row.set_sensitive(allow_signed or not is_ublue)
            prefer = self.imageRegistry.isUblueRef(booted_ref) and self.imageRegistry.isSignedTransport(booted_ref)
            if is_ublue and not allow_signed:
                self.signed_switch.set_active(False)
                self.signed_row.set_sensitive(False)
                self.signed_row.set_subtitle("Signed disabled: not on a uBlue base. Rebase unsigned first.")
            else:
                self.signed_switch.set_active(bool(prefer) if is_ublue else True)
                self.signed_row.set_subtitle("Uses ostree-image-signed when enabled")
                self.signed_row.set_sensitive(True)
        else:
            self.signed_row.set_sensitive(False)
            self.signed_switch.set_active(True)

    def on_source_changed(self, row, param):
        idx = row.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION:
            return
        src = self.sources[idx]
        self.current_source_id = src.get("id")

        self.types = self.imageRegistry.typesForSource(self.current_source_id)
        self.type_model.splice(0, self.type_model.get_n_items(), [])
        for t in self.types:
            self.type_model.append(t.get("name", t.get("id")))

        self.type_row.set_selected(0)
        self.update_ref()
        self.refresh_tags()
        self.apply_signature_default()

    def on_type_changed(self, row, param):
        self.update_ref()
        self.refresh_tags()
        self.apply_signature_default()

    def on_tag_mode_changed(self, row, param):
        idx = row.get_selected()
        self.use_version_tag = idx == 1
        self._fill_tag_model()
        self.update_ref()

    def on_tag_changed(self, row, param):
        self.update_ref()
        self.fetch_build_date()

    def _fill_tag_model(self):
        tags = self.available_versions if self.use_version_tag else self.available_streams
        if not tags:
            tags = self.available_streams or self.available_versions or ["latest"]
        preferred = getattr(self, "_preferred_tag", "")
        self.tag_model.splice(0, self.tag_model.get_n_items(), [])
        for tag in tags:
            self.tag_model.append(tag)
        if preferred and preferred in tags:
            self.tag_row.set_selected(tags.index(preferred))
            self._preferred_tag = ""
        elif self.tag_model.get_n_items() > 0:
            if not self.use_version_tag and "latest" in tags:
                self.tag_row.set_selected(tags.index("latest"))
            else:
                self.tag_row.set_selected(0)

    def update_ref(self):
        type_idx = self.type_row.get_selected()
        if type_idx == Gtk.INVALID_LIST_POSITION or not self.types:
            self.ref_row.set_subtitle("Invalid selection")
            return

        t = self.types[type_idx]
        image_ref = t.get("imageRef", "")

        tag_idx = self.tag_row.get_selected()
        tag = self.tag_model.get_string(tag_idx) if tag_idx != Gtk.INVALID_LIST_POSITION else "latest"

        is_signed = self.signed_switch.get_active()
        booted_ref = (
            (self.backend.bootedDeployment or {}).get("container-image-reference")
            or (self.backend.bootedDeployment or {}).get("ref")
            or ""
        )
        if self.imageRegistry.isUblueRef(image_ref) and is_signed and not self.imageRegistry.allowsSignedUblueTarget(booted_ref):
            is_signed = False

        self.full_ref = self.imageRegistry.constructRefSpec(image_ref, tag, is_signed)
        self.ref_row.set_subtitle(self.full_ref)

        if hasattr(self.backend, "needsPlasmaLoginPrep") and self.backend.needsPlasmaLoginPrep(self.full_ref):
            self.plasma_prep_row.set_visible(True)
        else:
            self.plasma_prep_row.set_visible(False)

    def refresh_tags(self):
        if not self.types:
            return
        type_idx = self.type_row.get_selected()
        if type_idx == Gtk.INVALID_LIST_POSITION:
            return
        image_ref = self.types[type_idx].get("imageRef", "")
        self._loading_tags = True
        self.build_date_row.set_subtitle("Fetching tags...")

        def done(_ref, tags, versions, _dates):
            def update():
                if image_ref != self._current_image_ref():
                    return GLib.SOURCE_REMOVE
                # streams ≈ non-version tags; versions from registry helper
                version_set = set(versions or [])
                streams = [t for t in (tags or []) if t not in version_set] or list(tags or [])
                self.available_streams = streams or ["latest", "stable"]
                self.available_versions = list(versions) if versions else [t for t in (tags or []) if t[:1].isdigit()] or list(tags or ["latest"])
                self._fill_tag_model()
                self._loading_tags = False
                self.update_ref()
                self.fetch_build_date()
                return GLib.SOURCE_REMOVE

            GLib.idle_add(update)

        def failed(_ref, error):
            def update():
                if image_ref != self._current_image_ref():
                    return GLib.SOURCE_REMOVE
                self.available_streams = ["latest", "stable", "beta"]
                self.available_versions = ["latest"]
                self._fill_tag_model()
                self._loading_tags = False
                self.build_date_row.set_subtitle(f"Tag fetch failed: {error}")
                self.update_ref()
                return GLib.SOURCE_REMOVE

            GLib.idle_add(update)

        self.imageRegistry.fetchTags(image_ref, done, failed)

    def _current_image_ref(self):
        type_idx = self.type_row.get_selected()
        if type_idx == Gtk.INVALID_LIST_POSITION or not self.types:
            return ""
        return self.types[type_idx].get("imageRef", "")

    def fetch_build_date(self):
        type_idx = self.type_row.get_selected()
        tag_idx = self.tag_row.get_selected()
        if type_idx == Gtk.INVALID_LIST_POSITION or tag_idx == Gtk.INVALID_LIST_POSITION or not self.types:
            return
        image_ref = self.types[type_idx].get("imageRef", "")
        tag = self.tag_model.get_string(tag_idx)
        if not image_ref or not tag:
            return
        self.build_date_row.set_subtitle("Fetching...")

        def ok(_ref, _tag, date):
            def update():
                if image_ref != self._current_image_ref() or tag != self._current_tag():
                    return False
                self.build_date_row.set_subtitle(date or "Unknown")
                return False

            GLib.idle_add(update)

        def err(_ref, _tag, error):
            def update():
                if image_ref != self._current_image_ref() or tag != self._current_tag():
                    return False
                self.build_date_row.set_subtitle("Unknown")
                return False

            GLib.idle_add(update)

        self.imageRegistry.fetchTagBuildDate(image_ref, tag, ok, err)

    def _current_tag(self):
        tag_idx = self.tag_row.get_selected()
        if tag_idx == Gtk.INVALID_LIST_POSITION:
            return ""
        return self.tag_model.get_string(tag_idx)

    def on_rebase_clicked(self, btn):
        if not self.full_ref:
            return
        self.refresh_overlay_choices()
        dialog = Adw.AlertDialog(
            heading="Confirm System Rebase",
            body=(
                f"Rebase the system to:\n\n{self.full_ref}\n\n"
                "A new deployment will be staged for reboot. Your home directory remains intact."
            ),
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("rebase", "Perform Rebase")
        dialog.set_response_appearance("rebase", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("cancel")

        if self.plasma_prep_row.get_visible():
            if self.plasma_prep_switch.get_active():
                dialog.set_body(
                    dialog.get_body()
                    + "\n\nPlasma login accounts will be prepared for the DE switch."
                )
            else:
                dialog.set_body(
                    dialog.get_body()
                    + "\n\nWarning: without preparing login accounts, Plasma login may fail."
                )

        def on_response(d, response):
            if response != "rebase":
                return
            if self.selected_overlay_id == "__reset_all__":
                self.backend.queuePendingOverlayReset()
            elif self.selected_overlay_id and self.overlay_service:
                s = self.overlay_service.getOverlaySet(self.selected_overlay_id)
                if s:
                    self.backend.queuePendingOverlaySet(
                        s.get("layeredPackages") or [],
                        s.get("localPackages") or [],
                        s.get("removedPackages") or [],
                    )
            options = {}
            if self.plasma_prep_row.get_visible():
                options["prepPlasmaLogin"] = self.plasma_prep_switch.get_active()
            self.backend.rebaseSystem(self.full_ref, options)

        dialog.connect("response", on_response)
        dialog.present(self.get_parent_window())
