from PyQt5.QtWidgets import QApplication
import sys
from ui.speed_meter import SpeedMeter

def main():
    app = QApplication(sys.argv)
    meter = SpeedMeter()
    meter.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
