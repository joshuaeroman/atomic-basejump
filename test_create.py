from basejump.core.overlays import OverlayService
from PyQt6.QtCore import QObject, pyqtSlot

s = OverlayService()
try:
    ret = s.createOverlaySet("test", "test", [], [], [])
    print("Success:", ret)
except Exception as e:
    print("Error:", e)
