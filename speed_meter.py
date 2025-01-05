import sys
import psutil
import time
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                            QPushButton, QDialog, QComboBox, QColorDialog, QHBoxLayout,QMenu,QSizePolicy,QLayout)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QMouseEvent
from speed_calculator import SpeedCalculator


class DraggableWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.dragging = False
        self.offset = QPoint()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.settings_button = QPushButton(' ', self)
        self.settings_button.setFixedSize(30, 30)
        self.settings_button.move(self.width() - 35, 5)
        self.settings_button.clicked.connect(self.open_settings)

        self.close_button = QPushButton(' ', self)
        self.close_button.setFixedSize(30, 30)
        self.close_button.move(self.width() - 65, 5)
        self.close_button.clicked.connect(self.close)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            self.move(self.mapToParent(event.pos() - self.offset))

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def contextMenuEvent(self, event):
        if event.reason() == event.Mouse:
            menu = QMenu(self)
            menu.addAction('Settings').triggered.connect(self.open_settings)
            menu.addAction('Close').triggered.connect(self.close)
            menu.exec(event.globalPos())

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

class SpeedThread(QThread):
    speed_signal = pyqtSignal(float, float, float)

    def __init__(self, speed_calculator):
        super().__init__()
        self.speed_calculator = speed_calculator
        self.running = True

    def run(self):
        while self.running:
            start_time = time.time()
            old_value = psutil.net_io_counters()
            time.sleep(1)
            new_value = psutil.net_io_counters()
            
            download_bytes = new_value.bytes_recv - old_value.bytes_recv
            upload_bytes = new_value.bytes_sent - old_value.bytes_sent
            
            download_speed = self.speed_calculator.calculate_speed(download_bytes)
            upload_speed = self.speed_calculator.calculate_speed(upload_bytes)
            
            elapsed_time = time.time() - start_time
            self.speed_signal.emit(download_speed, upload_speed, elapsed_time)

    def stop(self):
        self.running = False

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint)
        self.setWindowTitle('Settings')
        self.setFixedWidth(300)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 10px;
            }
            QLabel {
                font-size: 14px;
                color: #333333;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 5px;
                background-color: white;
                min-height: 25px;
            }
            QPushButton {
                padding: 8px;
                background-color: #f0f0f0;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Header with close button
        header_layout = QHBoxLayout()
        title_label = QLabel("Settings")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        close_button = QPushButton("×")
        close_button.setFixedSize(30, 30)
        close_button.setStyleSheet("""
            QPushButton {
                font-size: 20px;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #ffebeb;
                color: #ff4444;
            }
        """)
        close_button.clicked.connect(self.close)
        header_layout.addWidget(title_label)
        header_layout.addWidget(close_button)
        layout.addLayout(header_layout)

        # Text size settings
        self.text_size_label = QLabel('Text Size:')
        layout.addWidget(self.text_size_label)
        
        self.text_size_input = QComboBox()
        self.text_size_input.addItems(['Small', 'Medium', 'Large'])
        self.text_size_input.setCurrentText('Medium')
        layout.addWidget(self.text_size_input)

        # Unit settings
        self.unit_label = QLabel('Unit of Measurement:')
        layout.addWidget(self.unit_label)
        
        self.unit_input = QComboBox()
        self.unit_input.addItems(['Mbps', 'Kbps', 'MBps', 'kBps'])
        layout.addWidget(self.unit_input)

        # Background color settings
        self.bg_color_button = QPushButton('Choose Background Color')
        layout.addWidget(self.bg_color_button)
        self.bg_color_button.clicked.connect(self.choose_background_color)

        # Add some spacing
        layout.addSpacing(10)

        # Apply button
        self.apply_button = QPushButton('Apply')
        self.apply_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.apply_button.clicked.connect(self.apply_settings)
        layout.addWidget(self.apply_button)

        # Make dialog draggable
        self.dragging = False
        self.offset = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(self.mapToParent(event.pos() - self.offset))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def choose_background_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.parent().setStyleSheet(f"""
                QWidget#mainWidget {{
                    background-color: {color.name()};
                    border-radius: 10px;
                }}
            """)

    def apply_settings(self):
        text_size = {'Small': 25, 'Medium': 30, 'Large': 40}[self.text_size_input.currentText()]
        unit = self.unit_input.currentText()
        
        self.parent().set_text_size(text_size)
        self.parent().speed_calculator.set_unit(unit)
        self.parent().update_unit_labels()
        self.close()

class SpeedMeter(DraggableWidget):
    def __init__(self):
        super().__init__()
        self.speed_calculator = SpeedCalculator()
        self.speed_thread = None
        
        # Initialize all UI elements
        self.title_label = QLabel('Internet Speed Meter')
        self.download_label = QLabel('↓ 0 ' + self.speed_calculator.unit)
        self.upload_label = QLabel('↑ 0 ' + self.speed_calculator.unit)
        # self.settings_button = QPushButton('⚙')
        # self.close_button = QPushButton('×')
        
        self.initUI()
        self.start_measuring()

    def initUI(self):
        self.setWindowTitle('Internet Speed Meter')
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setMinimumSize(200, 80) 

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)  # Auto-adjust to content
        
        # Create main widget with background
        main_widget = QWidget()
        main_widget.setObjectName("mainWidget")
        main_widget.setStyleSheet("""
            QWidget#mainWidget {
                background-color: white;
                border-radius: 10px;
            }
            QPushButton {
                border: none;
                padding: 5px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)

        # Layout for main widget
        widget_layout = QVBoxLayout(main_widget)
        widget_layout.setContentsMargins(10, 10, 10, 10)

        # Header layout with title and buttons
        header_layout = QHBoxLayout()
        self.title_label.setFont(QFont('Arial', 12, QFont.Bold))
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        # Style the buttons
        self.settings_button.setFixedSize(30, 30)
        self.close_button.setFixedSize(30, 30)
        self.settings_button.setFont(QFont('Arial', 14))
        self.close_button.setFont(QFont('Arial', 14))
        
        header_layout.addWidget(self.settings_button)
        header_layout.addWidget(self.close_button)

        # Add layouts and widgets
        widget_layout.addLayout(header_layout)
        widget_layout.addWidget(self.download_label)
        widget_layout.addWidget(self.upload_label)
        widget_layout.addStretch()

        # Add main widget to main layout
        main_layout.addWidget(main_widget)

        # Connect buttons
        self.settings_button.clicked.connect(self.open_settings)
        self.close_button.clicked.connect(self.close)

        # Set initial styles
        self.set_text_size(30)

    def set_text_size(self, size):
        style = {
            'title': f'font-size: {size}px; color: #00698f; font-weight: bold;',
            'speed': f'font-size: {size-5}px; color: #008000;',
            'button': f'font-size: {size}px; color: #00698f;'
        }
        
        self.title_label.setStyleSheet(style['title'])
        self.download_label.setStyleSheet(style['speed'])
        self.upload_label.setStyleSheet(style['speed'])

    def update_unit_labels(self):
        try:
            current_download = float(self.download_label.text().split(':')[1].strip().split()[0])
            current_upload = float(self.upload_label.text().split(':')[1].strip().split()[0])
        except (ValueError, IndexError):
            return
        
        self.download_label.setText(f'↓ {current_download:.2f} {self.speed_calculator.unit}')
        self.upload_label.setText(f'↑ {current_upload:.2f} {self.speed_calculator.unit}')

    def start_measuring(self):
        if self.speed_thread is None or not self.speed_thread.isRunning():
            self.speed_thread = SpeedThread(self.speed_calculator)
            self.speed_thread.speed_signal.connect(self.update_speed_labels)
            self.speed_thread.start()

    def update_speed_labels(self, download_speed, upload_speed, elapsed_time):
        self.download_label.setText(
            f'↓ {download_speed:.2f} {self.speed_calculator.unit}'
        )
        self.upload_label.setText(
            f'↑ {upload_speed:.2f} {self.speed_calculator.unit}'
        )

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    def closeEvent(self, event):
        if self.speed_thread is not None:
            self.speed_thread.stop()
            self.speed_thread.wait()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    meter = SpeedMeter()
    meter.show()
    sys.exit(app.exec_())
