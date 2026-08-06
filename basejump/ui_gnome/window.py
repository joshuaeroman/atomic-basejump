import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

from basejump.core.ostree import OstreeBackend
from basejump.core.registry import ImageRegistryService
from basejump.core.settings import SettingsManager
from basejump.core.overlays import OverlayService

from .overview import OverviewPage
from .image_browser import ImageBrowserPage
from .overlay_sets import OverlaySetsPage
from .settings import SettingsPage
from .about import AboutPage

class BasejumpWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Atomic Basejump")
        self.set_default_size(960, 680)
        
        self.backend = OstreeBackend()
        self.imageRegistry = ImageRegistryService()
        self.settingsManager = SettingsManager()
        self.overlayService = OverlayService()

        self.split_view = Adw.NavigationSplitView()
        
        self.sidebar_page = Adw.NavigationPage.new(self.create_sidebar(), "Atomic Basejump")
        self.split_view.set_sidebar(self.sidebar_page)
        
        self.content_stack = Adw.ViewStack()
        
        # Navigation page wrapper for the content stack
        self.content_page = Adw.NavigationPage.new(self.content_stack, "Content")
        self.split_view.set_content(self.content_page)
        
        self.set_content(self.split_view)

        # Initialize pages
        self.overview_page = OverviewPage(self.backend, self.overlayService)
        self.image_browser_page = ImageBrowserPage(
            self.backend, self.imageRegistry, self.overlayService
        )
        self.overlay_sets_page = OverlaySetsPage(self.backend, self.overlayService)
        self.settings_page = SettingsPage(self.backend, self.settingsManager)
        self.about_page = AboutPage()
        
        self.content_stack.add_named(self.overview_page, "overview")
        self.content_stack.add_named(self.image_browser_page, "image_browser")
        self.content_stack.add_named(self.overlay_sets_page, "overlay_sets")
        self.content_stack.add_named(self.settings_page, "settings")
        self.content_stack.add_named(self.about_page, "about")
        
        self.switch_page("overview")
        
        # Start backend updates
        GLib.idle_add(self.backend.refreshStatus)

    def create_sidebar(self):
        toolbar = Adw.ToolbarView()
        
        header = Adw.HeaderBar()
        header.set_show_title(True)
        toolbar.add_top_bar(header)
        
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        listbox.set_css_classes(["navigation-sidebar"])
        listbox.connect("row-activated", self.on_sidebar_row_activated)
        
        self.sidebar_list = listbox
        
        rows = [
            ("overview", "Deployments", "drive-harddisk-symbolic"),
            ("image_browser", "Image Browser", "system-search-symbolic"),
            ("overlay_sets", "Overlay Sets", "emblem-system-symbolic"),
            ("settings", "Settings", "preferences-system-symbolic"),
            ("about", "About", "help-about-symbolic")
        ]
        
        for id, label, icon in rows:
            row = Gtk.ListBoxRow()
            row.set_name(id)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            box.set_margin_start(12)
            box.set_margin_end(12)
            box.set_margin_top(12)
            box.set_margin_bottom(12)
            
            img = Gtk.Image.new_from_icon_name(icon)
            box.append(img)
            
            lbl = Gtk.Label(label=label)
            box.append(lbl)
            
            row.set_child(box)
            listbox.append(row)
            
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(listbox)
        toolbar.set_content(scrolled)
        
        return toolbar

    def on_sidebar_row_activated(self, listbox, row):
        page_id = row.get_name()
        self.switch_page(page_id)

    def switch_page(self, page_id):
        self.content_stack.set_visible_child_name(page_id)
        
        # When switching pages on mobile layout, we might need to show the content.
        self.split_view.set_show_content(True)

