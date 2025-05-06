# Video Player + Enhanced AI-Based Highlight Detection
# Main application entry point

import sys
from PyQt5.QtWidgets import QApplication
from gui import VideoTranscriberEditor

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoTranscriberEditor()
    window.show()
    sys.exit(app.exec_())