import sys
import psutil
import time
import logging
from logging.handlers import RotatingFileHandler
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                            QPushButton, QDialog, QComboBox, QColorDialog, QHBoxLayout,
                            QMenu, QSizePolicy, QLayout, QSystemTrayIcon, QStyle, )
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal, QPoint, QSettings, QEvent
from PyQt5.QtGui import QFont, QMouseEvent
from speed_calculator import SpeedCalculator
import winreg
import threading

# Setup logging
def setup_logging():
    log_dir = os.path.join(os.path.expanduser('~'), '.netspeedmeter')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'netspeedmeter.log')
    
    handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger('NetSpeedMeter')
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger

logger = setup_logging()

class DraggableWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool |
            Qt.SubWindow  # Add SubWindow flag
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.dragging = False  # Add dragging attribute here

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = True  # Set dragging state
            self.drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = False  # Reset dragging state
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            # Save position after drag is complete
            if isinstance(self, SpeedMeter):  # Only save if it's the SpeedMeter
                self.settings.setValue('pos_x', self.pos().x())
                self.settings.setValue('pos_y', self.pos().y())
                self.settings.sync()

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
            # Modified menu options
            menu.addAction('Settings').triggered.connect(self.open_settings)
            menu.addAction('Hide').triggered.connect(self.hide)
            menu.exec(event.globalPos())

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    def setupMainWidget(self):
        # Make main widget pass through mouse events
        self.main_widget.setAttribute(Qt.WA_TransparentForMouseEvents)

    def showEvent(self, event):
        """Override show event to ensure window stays on top"""
        super().showEvent(event)
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool |
            Qt.SubWindow  # Add SubWindow flag
        )
        self.show()
        self.raise_()  # Bring window to top
        self.activateWindow()  # Activate window

class SpeedThread(QThread):
    # Change signal type to handle tuples with speed and unit
    speed_signal = pyqtSignal(tuple, tuple, float)

    def __init__(self, speed_calculator):
        super().__init__()
        self.speed_calculator = speed_calculator
        self.running = True
        self.current_interval = 0.5  # Reduced interval for more frequent updates
        self.last_bytes_recv = 0
        self.last_bytes_sent = 0
        self.last_measurement_time = time.time()
        self.min_sleep = 0.1  # Reduced minimum sleep time

    def run(self):
        while self.running:
            try:
                current_time = time.time()
                counters = psutil.net_io_counters()
                
                # Calculate byte differences
                bytes_recv_diff = counters.bytes_recv - self.last_bytes_recv
                bytes_sent_diff = counters.bytes_sent - self.last_bytes_sent
                interval = current_time - self.last_measurement_time
                
                # Only update if there's actual data
                if bytes_recv_diff >= 0 and bytes_sent_diff >= 0 and interval > 0:
                    # Update stored values before calculating speed
                    self.last_bytes_recv = counters.bytes_recv
                    self.last_bytes_sent = counters.bytes_sent
                    self.last_measurement_time = current_time
                    
                    # Calculate speeds
                    download = self.speed_calculator.calculate_speed(bytes_recv_diff, interval)
                    upload = self.speed_calculator.calculate_speed(bytes_sent_diff, interval)
                    
                    # Emit signal with speed data
                    self.speed_signal.emit(download, upload, interval)
                
                time.sleep(self.min_sleep)
                
            except Exception as e:
                logger.error(f"Error in speed measurement: {str(e)}")
                time.sleep(1)

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
        
        # Update unit options to only show byte-based units
        self.unit_input = QComboBox()
        self.unit_input.addItems(['MB/s', 'KB/s'])
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
        try:
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
            self.unit_suffix = '/s'  # This won't be used anymore as unit comes from speed_calculator
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
            self.setWindowFlags(
                Qt.FramelessWindowHint | 
                Qt.WindowStaysOnTopHint | 
                Qt.Tool |
                Qt.SubWindow  # Add SubWindow flag
            )
            self.show()
            self.raise_()
            self.activateWindow()

            # Add recovery mechanism for settings
            self.load_settings()
            
            # Add startup management
            self.startup_registry_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            self.app_name = "InternetSpeedMeter"
            self.load_startup_setting()
            
        except Exception as e:
            logger.error(f"Error initializing SpeedMeter: {str(e)}")
            raise

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
        self.setupMainWidget()  # Add this line to make widget pass through events
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


    def keep_on_top(self):
        while True:
            self.raise_()
            self.activateWindow()
            time.sleep(0.1)  # adjust the sleep time as needed


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
            current_download = float(self.download_label.text().split()[1])
            current_upload = float(self.upload_label.text().split()[1])
        except (ValueError, IndexError):
            return
        
        self.download_label.setText(f'↓ {self.format_speed(current_download)}')
        self.upload_label.setText(f'↑ {self.format_speed(current_upload)}')

    def start_measuring(self):
        if self.speed_thread is None or not self.speed_thread.isRunning():
            self.speed_thread = SpeedThread(self.speed_calculator)
            self.speed_thread.speed_signal.connect(self.update_speed_labels)
            self.speed_thread.start()

    def format_speed(self, speed, unit):
        """Format speed with proper precision"""
        if speed < 0.1:
            return f'0.00 {unit}'
        elif speed < 10:
            return f'{speed:.2f} {unit}'
        elif speed < 100:
            return f'{speed:.1f} {unit}'
        else:
            return f'{speed:.0f} {unit}'

    def update_speed_labels(self, download_data, upload_data, elapsed_time):
        try:
            current_time = time.time()
            if current_time - self.last_update < self.update_threshold:
                return
                
            self.last_update = current_time
            
            download_speed, download_unit = download_data
            upload_speed, upload_unit = upload_data
            
            download_text = self.format_speed_label((download_speed, download_unit), 'down')
            upload_text = self.format_speed_label((upload_speed, upload_unit), 'up')
            
            self.download_label.setText(download_text)
            self.upload_label.setText(upload_text)
        except Exception as e:
            logger.error(f"Error updating speed labels: {str(e)}")
            self.download_label.setText("↓ Error")
            self.upload_label.setText("↑ Error")

    def format_speed_label(self, speed_data, direction='down'):
        """Format speed label with colored or plain arrows"""
        speed, unit = speed_data
        speed_text = self.format_speed(speed, unit)
        arrow = '↓' if direction == 'down' else '↑'
        
        if self.show_colored_arrows:
            color = self.download_color if direction == 'down' else self.upload_color
            return f'<span style="color: {color}">{arrow}</span> {speed_text}'
        return f'{arrow} {speed_text}'

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
        try:
            # Save settings before closing
            self.settings.setValue('font_size', self.current_font_size)
            self.settings.setValue('opacity', self.opacity)
            self.settings.setValue('theme', self.current_theme)
            self.settings.setValue('colored_arrows', self.show_colored_arrows)
            self.settings.sync()
            
            if self.allow_close:  # Fixed syntax error here
                # Stop thread and remove tray icon before closing
                if self.speed_thread is not None:
                    self.speed_thread.stop()
                    self.speed_thread.wait()
                if hasattr(self, 'tray_icon'):
                    self.tray_icon.hide()
                event.accept()
            else:
                # Just minimize to tray
                self.hide()
                event.ignore()
        except Exception as e:
            logger.error(f"Error during application close: {str(e)}")
            event.accept()

    def enterEvent(self, event):
        self.opacity = self.hover_opacity
        self.apply_theme(self.current_theme)

    def leaveEvent(self, event):
        self.opacity = self.normal_opacity
        self.apply_theme(self.current_theme)

    def setup_tray(self):
        """Setup system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_DriveNetIcon))
        
        # Create tray menu
        self.tray_menu = QMenu()  # Make it instance variable to prevent garbage collection
        self.tray_menu.setStyleSheet("""
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
        
        # Add menu actions with proper connections
        show_action = self.tray_menu.addAction('Show')
        show_action.triggered.connect(self.show_and_raise)  # Use new method
        settings_action = self.tray_menu.addAction('Settings')
        settings_action.triggered.connect(self.open_settings)
        self.tray_menu.addSeparator()
        quit_action = self.tray_menu.addAction('Quit')
        quit_action.triggered.connect(self.quit_application)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        """Handle tray icon activation"""
        # Changed to handle single click and double click
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if not self.isVisible():
                self.show()
                self.raise_()
                self.activateWindow()
            else:
                self.hide()

    def quit_application(self):
        """Properly quit the application"""
        try:
            # Save settings before quitting
            self.settings.sync()
            
            # Stop the speed measurement thread
            if self.speed_thread is not None:
                self.speed_thread.running = False
                self.speed_thread.wait()
            
            # Remove tray icon before quitting
            if hasattr(self, 'tray_icon'):
                self.tray_icon.hide()
            
            # Actually quit the application
            QApplication.quit()
            
        except Exception as e:
            logger.error(f"Error during application quit: {str(e)}")
            # Force quit if there's an error
            QApplication.quit()

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

    def load_settings(self):
        try:
            self.current_font_size = self.settings.value('font_size', 30, type=int)
            self.opacity = self.settings.value('opacity', 0.8, type=float)
            self.current_theme = self.settings.value('theme', 'dark', type=str)
            self.show_colored_arrows = self.settings.value('colored_arrows', True, type=bool)
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
            # Use defaults if settings load fails
            self.current_font_size = 30
            self.opacity = 0.8
            self.current_theme = 'dark'
            self.show_colored_arrows = True

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

    def load_startup_setting(self):
        """Load startup setting from registry"""
        try:
            self.auto_start = self.is_in_startup()
            self.settings.setValue('auto_start', self.auto_start)
        except Exception as e:
            logger.error(f"Error loading startup setting: {e}")
            self.auto_start = False

    def toggle_startup(self, enable=None):
        """Toggle startup status"""
        if enable is None:
            enable = not self.is_in_startup()
            
        try:
            if enable:
                self.add_to_startup()
            else:
                self.remove_from_startup()
                
            self.auto_start = enable
            self.settings.setValue('auto_start', enable)
            return True
        except Exception as e:
            logger.error(f"Error toggling startup: {e}")
            return False

    def is_in_startup(self):
        """Check if app is in startup registry"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.startup_registry_path,
                0,
                winreg.KEY_READ
            )
            value, _ = winreg.QueryValueEx(key, self.app_name)
            winreg.CloseKey(key)
            return value == self.get_executable_path()
        except WindowsError:
            return False

    def add_to_startup(self):
        """Add app to startup registry"""
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            self.startup_registry_path,
            0,
            winreg.KEY_WRITE
        )
        winreg.SetValueEx(
            key,
            self.app_name,
            0,
            winreg.REG_SZ,
            self.get_executable_path()
        )
        winreg.CloseKey(key)

    def remove_from_startup(self):
        """Remove app from startup registry"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.startup_registry_path,
                0,
                winreg.KEY_WRITE
            )
            winreg.DeleteValue(key, self.app_name)
            winreg.CloseKey(key)
        except WindowsError:
            pass

    def get_executable_path(self):
        """Get path to executable"""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            return sys.executable
        else:
            # Running as script
            return f'pythonw "{os.path.abspath(__file__)}"'

    def show(self):
        """Override show method to ensure window stays on top"""
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool |
            Qt.SubWindow  # Add SubWindow flag
        )
        super().show()
        # threading.Thread(target=self.keep_on_top).start()
        self.raise_()
        self.activateWindow()

    def show_and_raise(self):
        """Show window and ensure it's on top"""
        self.show()
        self.raise_()
        self.activateWindow()

    def changeEvent(self, event):
        """Override change event to ensure window stays on top"""
        if event.type() == QEvent.WindowStateChange:
            self.raise_()
            self.activateWindow()
        super().changeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    meter = SpeedMeter()
    meter.show()
    sys.exit(app.exec_())

