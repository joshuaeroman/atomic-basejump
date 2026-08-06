import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, Gdk

from .window import BasejumpWindow

def on_activate(app):
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(b"""
    .chip-layered { background-color: alpha(@accent_bg_color, 0.2); border: 1px solid @accent_bg_color; }
    .chip-layered label { color: @accent_color; }
    .chip-local { background-color: alpha(@success_bg_color, 0.2); border: 1px solid @success_bg_color; }
    .chip-local label { color: @success_color; }
    .chip-removed { background-color: alpha(@error_bg_color, 0.2); border: 1px solid @error_bg_color; }
    .chip-removed label { color: @error_color; }
    """)
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    
    win = BasejumpWindow(application=app)
    win.present()

def on_open(app, files, n_files, hint):
    on_activate(app)

def main():
    app = Adw.Application(
        application_id='io.github.joshuaroman.AtomicBasejump',
        flags=Gio.ApplicationFlags.HANDLES_OPEN
    )
    app.connect('activate', on_activate)
    app.connect('open', on_open)
    sys.exit(app.run(sys.argv))

if __name__ == '__main__':
    main()
