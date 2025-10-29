import os
import sys

# Render without a display
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from atr_utility.gui import ATRStudioWindow


def main() -> None:
    app = QApplication(sys.argv)
    w = ATRStudioWindow()
    w.show()  # required before grab
    app.processEvents()
    pix = w.grab()
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "atr_studio_screenshot.png"))
    pix.save(out)
    print(out)


if __name__ == "__main__":
    main()
