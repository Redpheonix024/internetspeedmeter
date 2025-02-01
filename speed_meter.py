import sys
import psutil
import time
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                            QPushButton, QDialog, QComboBox, QColorDialog, QHBoxLayout,
                            QMenu, QSizePolicy, QLayout, QSystemTrayIcon, QStyle)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal, QPoint, QSettings
from PyQt5.QtGui import QFont, QMouseEvent
from speed_calculator import SpeedCalculator


class DraggableWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.dragging = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.ArrowCursor)  # Set default cursor

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.setCursor(Qt.ClosedHandCursor)  # Change cursor while dragging
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.setCursor(Qt.ArrowCursor)  # Restore cursor
            event.accept()

    def contextMenuEvent(self, event):
        if event.reason() == event.Mouse:
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: white;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    padding: 5px;
                }
                QMenu::item {
                    padding: 5px 20px;
                    border-radius: 3px;
                }
                QMenu::item:selected {
                    background-color: #e0e0e0;
                }
            """)
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
        self.speed_buffer_size = 5  # Number of samples to average
        self.download_buffer = []
        self.upload_buffer = []
        self.min_interval = 0.5  # Minimum update interval in seconds
        self.max_interval = 2.0   # Maximum update interval in seconds
        self.current_interval = 1.0  # Current update interval
        self.byte_multiplier = 1  # Keep bytes as is, we'll convert in format_speed

    def run(self):
        while self.running:
            start_time = time.time()
            old_value = psutil.net_io_counters()
            time.sleep(self.current_interval)
            new_value = psutil.net_io_counters()
            
            download_bytes = new_value.bytes_recv - old_value.bytes_recv
            upload_bytes = new_value.bytes_sent - old_value.bytes_sent
            
            # Calculate speeds in KB/s
            download_speed = (download_bytes * self.byte_multiplier) / self.current_interval
            upload_speed = (upload_bytes * self.byte_multiplier) / self.current_interval
            
            # Update buffers
            self.download_buffer.append(download_speed)
            self.upload_buffer.append(upload_speed)
            
            # Keep buffer at fixed size
            if len(self.download_buffer) > self.speed_buffer_size:
                self.download_buffer.pop(0)
            if len(self.upload_buffer) > self.speed_buffer_size:
                self.upload_buffer.pop(0)
            
            # Calculate averaged speeds
            avg_download = sum(self.download_buffer) / len(self.download_buffer)
            avg_upload = sum(self.upload_buffer) / len(self.upload_buffer)
            
            # Adapt update interval based on speed changes
            speed_change = abs(avg_download - download_speed) / max(avg_download, 0.1)
            if speed_change > 0.5:  # If speed changed by more than 50%
                self.current_interval = max(self.min_interval, self.current_interval * 0.8)
            else:
                self.current_interval = min(self.max_interval, self.current_interval * 1.1)
            
            elapsed_time = time.time() - start_time
            self.speed_signal.emit(avg_download, avg_upload, elapsed_time)

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
        self.hover_opacity = 1.0
        self.normal_opacity = 0.8
        self.opacity = self.normal_opacity
        self.current_theme = 'dark'  # Changed default theme to dark
        self.current_font_size = 30
        self.last_update = time.time()
        self.update_threshold = 0.1  # Minimum time between updates in seconds
        self.unit_suffix = 'B/s'  # Base unit suffix
        self.bytes_in_kb = 1024
        self.bytes_in_mb = 1024 * 1024
        self.text_color = '#E0E0E0'  # Default text color
        self.download_color = '#ff4444'  # Red for download
        self.upload_color = '#4CAF50'    # Green for upload
        self.show_colored_arrows = True
        self.settings = QSettings('NetSpeedMeter', 'Settings')
        self.allow_close = False  # Add flag to control actual closing
        
        # Initialize only speed labels
        self.download_label = QLabel('↓ 0 ' + self.speed_calculator.unit)
        self.upload_label = QLabel('↑ 0 ' + self.speed_calculator.unit)
        
        self.initUI()
        self.load_position()  # Load position before showing
        self.start_measuring()
        
        # Setup system tray
        self.setup_tray()
        
        # Load position before showing
        self.load_position()

        # Ensure window stays on top even after losing focus
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)

    def initUI(self):
        self.setWindowTitle('Internet Speed Meter')
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setMinimumSize(180, 60)  # Reduced size since we removed the title

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        
        # Create and setup main widget with background
        self.main_widget = QWidget()
        self.main_widget.setObjectName("mainWidget")
        widget_layout = QVBoxLayout(self.main_widget)
        widget_layout.setContentsMargins(10, 5, 10, 5)  # Reduced vertical margins
        widget_layout.setSpacing(2)  # Reduced spacing between labels

        # Add only speed labels
        widget_layout.addWidget(self.download_label)
        widget_layout.addWidget(self.upload_label)

        # Add main widget to main layout
        main_layout.addWidget(self.main_widget)
        
        # Apply theme and styles
        self.apply_theme(self.current_theme)
        self.set_text_size(self.current_font_size)

    def apply_theme(self, theme_name, custom_colors=None):
        self.current_theme = theme_name
        opacity = int(self.opacity * 255)
        
        if theme_name == 'light':
            bg_color = f'rgba(240, 240, 240, {opacity})'
            text_color = '#333333'
        elif theme_name == 'dark':
            bg_color = f'rgba(0, 0, 0, {opacity})'
            text_color = '#E0E0E0'
        elif theme_name == 'custom' and custom_colors:
            # Fix the rgba syntax for custom colors
            r, g, b = int(custom_colors["bg"][1:3], 16), int(custom_colors["bg"][3:5], 16), int(custom_colors["bg"][5:7], 16)
            bg_color = f'rgba({r}, {g}, {b}, {opacity})'
            text_color = custom_colors.get("text", self.text_color)  # Use custom text color if provided
        
        self.main_widget.setStyleSheet(f"""
            QWidget#mainWidget {{
                background-color: {bg_color};
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)
        
        self.set_text_color(text_color)

    def set_text_color(self, color):
        self.text_color = color
        style = f'font-size: {self.current_font_size-5}px; color: {self.text_color};'
        self.download_label.setStyleSheet(style)
        self.upload_label.setStyleSheet(style)

    def set_opacity(self, value):
        self.opacity = value / 100.0
        self.apply_theme(self.current_theme)

    def set_text_size(self, size):
        self.current_font_size = size
        style = f'font-size: {size-5}px; color: #008000;'
        self.download_label.setStyleSheet(style)
        self.upload_label.setStyleSheet(style)

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

    def format_speed_label(self, speed, direction='down'):
        """Format speed label with colored or plain arrows"""
        speed_text = self.format_speed(speed)
        arrow = '↓' if direction == 'down' else '↑'
        
        if self.show_colored_arrows:
            color = self.download_color if direction == 'down' else self.upload_color
            return f'<span style="color: {color}">{arrow}</span> {speed_text}'
        return f'{arrow} {speed_text}'

    def update_speed_labels(self, download_speed, upload_speed, elapsed_time):
        current_time = time.time()
        if current_time - self.last_update < self.update_threshold:
            return
            
        self.last_update = current_time
        
        download_text = self.format_speed_label(download_speed, 'down')
        upload_text = self.format_speed_label(upload_speed, 'up')
        
        self.download_label.setText(download_text)
        self.upload_label.setText(upload_text)

    def format_speed(self, speed):
        """Format speed in B/s, KB/s or MB/s"""
        if speed >= self.bytes_in_mb:  # More than 1MB/s
            return f'{speed/self.bytes_in_mb:.1f} M{self.unit_suffix}'
        elif speed >= self.bytes_in_kb:  # More than 1KB/s
            return f'{speed/self.bytes_in_kb:.1f} K{self.unit_suffix}'
        else:
            return f'{speed:.0f} {self.unit_suffix}'

    def toggle_colored_arrows(self, enabled):
        """Toggle colored arrows on/off"""
        self.show_colored_arrows = enabled
        self.update_speed_labels(
            float(self.download_label.text().split()[1]), 
            float(self.upload_label.text().split()[1]), 
            0
        )

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    def closeEvent(self, event):
        """Handle application closing"""
        if self.allow_close:
            # Actually close the application
            if self.speed_thread is not None:
                self.speed_thread.stop()
                self.speed_thread.wait()
            event.accept()
        else:
            # Just minimize to tray
            self.hide()
            event.ignore()

    def enterEvent(self, event):
        self.opacity = self.hover_opacity
        self.apply_theme(self.current_theme)

    def leaveEvent(self, event):
        self.opacity = self.normal_opacity
        self.apply_theme(self.current_theme)

    def setup_tray(self):
        """Setup system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon(self)
        # Use network icon instead of computer icon
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_DriveNetIcon))
        
        # Create tray menu
        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #e0e0e0;
            }
        """)
        
        # Add menu actions
        settings_action = tray_menu.addAction('Settings')
        settings_action.triggered.connect(self.open_settings)
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction('Quit')
        quit_action.triggered.connect(self.quit_application)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def quit_application(self):
        """Properly quit the application"""
        self.allow_close = True
        self.close()

    def position_window(self):
        """Position window in bottom right of screen"""
        screen = QApplication.primaryScreen().geometry()
        window_size = self.geometry()
        taskbar_height = 40  # Estimated taskbar height
        
        # Calculate position (bottom right with small margin)
        x = screen.width() - window_size.width() - 10
        y = screen.height() - window_size.height() - 10
        
        self.move(x, y)

    def load_position(self):
        """Load saved window position"""
        pos_x = self.settings.value('pos_x', None, type=int)  # Specify type as int
        pos_y = self.settings.value('pos_y', None, type=int)
        
        if pos_x is not None and pos_y is not None:
            screen = QApplication.primaryScreen().geometry()
            # Ensure window is visible on screen
            pos_x = min(max(0, pos_x), screen.width() - self.width())
            pos_y = min(max(0, pos_y), screen.height() - self.height())
            self.move(pos_x, pos_y)
        else:
            self.position_window()

    def moveEvent(self, event):
        """Called whenever the window is moved"""
        super().moveEvent(event)
        # Save position after move is complete
        if not self.dragging:  # Only save when not dragging to avoid excessive writes
            self.settings.setValue('pos_x', self.pos().x())
            self.settings.setValue('pos_y', self.pos().y())
            self.settings.sync()  # Force settings to be written immediately

    def mouseMoveEvent(self, event: QMouseEvent):
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        super().mouseReleaseEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    meter = SpeedMeter()
    meter.show()
    sys.exit(app.exec_())
