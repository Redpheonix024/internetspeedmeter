from PyQt5.QtWidgets import (QDialog, QLabel, QVBoxLayout, QPushButton, 
                            QComboBox, QColorDialog, QHBoxLayout, QSpinBox, QSlider, QCheckBox)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QColor

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint)
        self.setWindowTitle('Settings')
        self.setFixedWidth(300)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Enhanced styling
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                border-radius: 10px;
                border: 1px solid #ddd;
            }
            QLabel {
                color: #333;
                font-size: 14px;
                margin-top: 10px;
            }
            QComboBox, QPushButton {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 5px;
                background-color: white;
                min-width: 100px;
            }
            QComboBox:hover, QPushButton:hover {
                border-color: #999;
                background-color: #f0f0f0;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #ddd;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #2196F3;
                border: none;
                width: 16px;
                height: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #1976D2;
            }
        """)

        # Create sections with headers
        self.add_section_header("Display", layout)
        
        # Theme settings
        self.theme_label = QLabel("Theme:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Light', 'Dark', 'Custom'])
        self.theme_combo.setCurrentText(parent.current_theme.capitalize())
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(self.theme_label)
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)

        # Colors section
        colors_layout = QHBoxLayout()
        self.bg_color_button = QPushButton('Background Color')
        self.text_color_button = QPushButton('Text Color')
        colors_layout.addWidget(self.bg_color_button)
        colors_layout.addWidget(self.text_color_button)
        layout.addLayout(colors_layout)

        # Arrow color toggle
        self.colored_arrows_checkbox = QCheckBox("Show Colored Arrows")
        self.colored_arrows_checkbox.setChecked(parent.show_colored_arrows)
        layout.addWidget(self.colored_arrows_checkbox)

        # Add spacing
        layout.addSpacing(10)

        # Add transparency control
        self.opacity_label = QLabel('Opacity:')
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(int(parent.opacity * 100))
        layout.addWidget(self.opacity_label)
        layout.addWidget(self.opacity_slider)

        # Text size settings
        self.text_size_label = QLabel('Text Size:')
        self.text_size_input = QComboBox()
        self.text_size_input.addItems(['Small', 'Medium', 'Large'])
        self.text_size_input.setCurrentText('Medium')
        layout.addWidget(self.text_size_label)
        layout.addWidget(self.text_size_input)

        # Unit settings
        self.unit_label = QLabel('Unit of Measurement:')
        self.unit_input = QComboBox()
        self.unit_input.addItems(['KB/s', 'MB/s'])
        layout.addWidget(self.unit_label)
        layout.addWidget(self.unit_input)

        # Apply button
        layout.addSpacing(10)
        self.apply_button = QPushButton('Apply')
        self.apply_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 10px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.apply_button)

        # Connect signals
        self.bg_color_button.clicked.connect(self.choose_background_color)
        self.text_color_button.clicked.connect(self.choose_text_color)
        self.theme_combo.currentTextChanged.connect(self.handle_theme_change)
        self.apply_button.clicked.connect(self.apply_settings)
        self.opacity_slider.valueChanged.connect(self.update_opacity)

    def update_opacity(self, value):
        self.parent().set_opacity(value)

    def choose_text_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.parent().set_text_color(color.name())
            # Update custom colors if in custom theme
            if self.parent().current_theme == 'custom':
                self.custom_colors = getattr(self, 'custom_colors', {})
                self.custom_colors['text'] = color.name()

    def choose_background_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.custom_colors = getattr(self, 'custom_colors', {})
            self.custom_colors['bg'] = color.name()
            self.apply_custom_theme()

    def apply_custom_theme(self):
        if hasattr(self, 'custom_colors'):
            self.parent().apply_theme('custom', self.custom_colors)

    def handle_theme_change(self, theme_name):
        if theme_name in ['Light', 'Dark']:
            self.parent().apply_theme(theme_name.lower())
        else:
            self.apply_custom_theme()

    def apply_settings(self):
        text_size = {'Small': 25, 'Medium': 30, 'Large': 40}[self.text_size_input.currentText()]
        unit = self.unit_input.currentText()
        
        self.parent().set_text_size(text_size)
        self.parent().speed_calculator.set_unit(unit)
        self.parent().toggle_colored_arrows(self.colored_arrows_checkbox.isChecked())
        self.parent().update_unit_labels()
        self.close()

    def add_section_header(self, text, layout):
        header = QLabel(text)
        header.setStyleSheet("""
            QLabel {
                color: #2196F3;
                font-size: 16px;
                font-weight: bold;
                border-bottom: 2px solid #2196F3;
                padding-bottom: 5px;
                margin-top: 15px;
            }
        """)
        layout.addWidget(header)
