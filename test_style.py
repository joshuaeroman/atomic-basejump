import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtQuickControls2 import QQuickStyle

def main():
    print("Available styles:", QQuickStyle.availableStyles())

if __name__ == "__main__":
    main()
