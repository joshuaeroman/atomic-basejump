import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from basejump.core.appinfo import AppInfo


class AboutPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        info = AppInfo()

        self.toolbar = Adw.ToolbarView()
        self.header = Adw.HeaderBar()
        self.header.set_show_title(True)
        self.title_widget = Adw.WindowTitle(title="About")
        self.header.set_title_widget(self.title_widget)
        self.toolbar.add_top_bar(self.header)

        self.status_page = Adw.StatusPage()
        self.status_page.set_title(info.display_name)
        self.status_page.set_description(
            "An rpm-ostree deployment manager for Fedora Atomic.\n"
            f"Version: {info.version}\n"
            f"Build Time: {info.build_timestamp}\n"
            f"License: {info.license}\n"
            f"{info.homepage}"
        )
        self.status_page.set_icon_name("io.github.joshuaroman.AtomicBasejump")

        self.toolbar.set_content(self.status_page)
        self.toolbar.set_vexpand(True)
        self.append(self.toolbar)
