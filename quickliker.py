"""
Auto Clicker - Кроссплатформенное приложение для macOS и Windows
Установка зависимостей: pip install PyQt6 pynput
Запуск: python auto_clicker.py
Сборка: pyinstaller --onefile --windowed --name="AutoClicker" auto_clicker.py
"""

import sys
import time
from threading import Thread
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QPushButton, QSpinBox, QRadioButton, 
                             QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QSlider)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QPalette, QColor
from pynput import mouse, keyboard
from pynput.keyboard import Key, KeyCode


class ClickerSignals(QObject):
    """Сигналы для обновления UI из другого потока"""
    status_changed = pyqtSignal(bool)


class AutoClicker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.signals = ClickerSignals()
        self.signals.status_changed.connect(self.update_status)
        
        # Настройки
        self.clicks_per_second = 10
        self.mouse_button = mouse.Button.left
        self.hold_mode = False
        self.hotkey = 'option+-'  # По умолчанию Option + -
        
        # Состояние
        self.is_active = False
        self.click_thread = None
        self.mouse_controller = mouse.Controller()
        self.current_keys = set()
        
        # Настройка UI
        self.init_ui()
        
        # Запуск слушателя клавиатуры
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        self.keyboard_listener.start()
        
    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle('Auto Clicker')
        self.setFixedSize(520, 680)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(18)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Заголовок
        title = QLabel('🖱️ Auto Clicker')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Статус
        self.status_label = QLabel('⚪ ВЫКЛЮЧЕН')
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                color: #666;
                padding: 25px;
                border-radius: 15px;
                font-weight: bold;
                font-size: 22px;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Частота кликов с ползунком
        cps_group = QGroupBox('⚡ Частота кликов')
        cps_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
        cps_layout = QVBoxLayout()
        
        # Большой дисплей
        self.cps_display = QLabel(f'{self.clicks_per_second}')
        self.cps_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cps_display.setStyleSheet("""
            QLabel { 
                font-size: 48px; 
                color: #667eea; 
                font-weight: bold;
                padding: 10px;
            }
        """)
        cps_layout.addWidget(self.cps_display)
        
        # Подпись
        cps_label = QLabel('кликов в секунду')
        cps_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cps_label.setStyleSheet("QLabel { font-size: 14px; color: #999; }")
        cps_layout.addWidget(cps_label)
        
        # Ползунок
        self.cps_slider = QSlider(Qt.Orientation.Horizontal)
        self.cps_slider.setRange(1, 100)
        self.cps_slider.setValue(10)
        self.cps_slider.setMinimumHeight(40)
        self.cps_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #e0e0e0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #667eea;
                width: 24px;
                height: 24px;
                margin: -8px 0;
                border-radius: 12px;
            }
            QSlider::handle:horizontal:hover {
                background: #5568d3;
            }
        """)
        self.cps_slider.valueChanged.connect(self.update_cps)
        cps_layout.addWidget(self.cps_slider)
        
        # SpinBox для точного ввода
        spinbox_layout = QHBoxLayout()
        spinbox_layout.addStretch()
        self.cps_spinbox = QSpinBox()
        self.cps_spinbox.setRange(1, 100)
        self.cps_spinbox.setValue(10)
        self.cps_spinbox.setMinimumHeight(40)
        self.cps_spinbox.setMinimumWidth(100)
        self.cps_spinbox.setStyleSheet("QSpinBox { font-size: 16px; padding: 5px; }")
        self.cps_spinbox.valueChanged.connect(self.update_cps_from_spinbox)
        spinbox_layout.addWidget(QLabel('Точное значение:'))
        spinbox_layout.addWidget(self.cps_spinbox)
        spinbox_layout.addStretch()
        cps_layout.addLayout(spinbox_layout)
        
        cps_group.setLayout(cps_layout)
        layout.addWidget(cps_group)
        
        # Кнопка мыши - БОЛЬШИЕ кнопки
        button_group = QGroupBox('🖱️ Выберите кнопку мыши')
        button_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.left_radio = QRadioButton('ЛЕВАЯ')
        self.right_radio = QRadioButton('ПРАВАЯ')
        self.left_radio.setChecked(True)
        self.left_radio.setMinimumHeight(60)
        self.right_radio.setMinimumHeight(60)
        self.left_radio.setStyleSheet("""
            QRadioButton {
                font-size: 18px;
                font-weight: bold;
                padding: 15px;
            }
            QRadioButton::indicator {
                width: 25px;
                height: 25px;
            }
        """)
        self.right_radio.setStyleSheet("""
            QRadioButton {
                font-size: 18px;
                font-weight: bold;
                padding: 15px;
            }
            QRadioButton::indicator {
                width: 25px;
                height: 25px;
            }
        """)
        self.left_radio.toggled.connect(self.update_settings)
        button_layout.addWidget(self.left_radio)
        button_layout.addWidget(self.right_radio)
        button_group.setLayout(button_layout)
        layout.addWidget(button_group)
        
        # Режим удержания
        mode_group = QGroupBox('⚙️ Режим работы')
        mode_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
        mode_layout = QVBoxLayout()
        self.hold_checkbox = QCheckBox('Режим удержания (зажать кнопку)')
        self.hold_checkbox.setMinimumHeight(50)
        self.hold_checkbox.setStyleSheet("""
            QCheckBox { 
                font-size: 16px; 
                padding: 10px;
            }
            QCheckBox::indicator {
                width: 25px;
                height: 25px;
            }
        """)
        self.hold_checkbox.stateChanged.connect(self.update_settings)
        mode_layout.addWidget(self.hold_checkbox)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Горячая клавиша
        hotkey_group = QGroupBox('⌨️ Горячая клавиша')
        hotkey_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
        hotkey_layout = QVBoxLayout()
        
        self.hotkey_combo = QComboBox()
        self.hotkey_combo.addItems([
            'Option + -',
            'F6',
            'F7', 
            'F8', 
            'F9', 
            'F10', 
            'F11', 
            'F12'
        ])
        self.hotkey_combo.setCurrentText('Option + -')
        self.hotkey_combo.setMinimumHeight(50)
        self.hotkey_combo.setStyleSheet("QComboBox { font-size: 16px; padding: 10px; }")
        self.hotkey_combo.currentTextChanged.connect(self.update_hotkey)
        hotkey_layout.addWidget(self.hotkey_combo)
        
        hotkey_group.setLayout(hotkey_layout)
        layout.addWidget(hotkey_group)
        
        # Подсказка
        hint = QLabel('💡 Нажмите Option + - для включения/выключения')
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("QLabel { color: #999; font-size: 14px; margin-top: 10px; }")
        self.hint_label = hint
        layout.addWidget(hint)
        
        layout.addStretch()
        
        # Применение стилей
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
            }
            QWidget {
                background-color: white;
                border-radius: 20px;
            }
            QGroupBox {
                font-weight: bold;
                color: #555;
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                margin-top: 15px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }
        """)
    
    def update_cps(self, value):
        """Обновление CPS из ползунка"""
        self.clicks_per_second = value
        self.cps_display.setText(f'{value}')
        self.cps_spinbox.blockSignals(True)
        self.cps_spinbox.setValue(value)
        self.cps_spinbox.blockSignals(False)
        
        if self.is_active and not self.hold_mode:
            self.stop_clicking()
            self.start_clicking()
    
    def update_cps_from_spinbox(self, value):
        """Обновление CPS из spinbox"""
        self.clicks_per_second = value
        self.cps_display.setText(f'{value}')
        self.cps_slider.blockSignals(True)
        self.cps_slider.setValue(value)
        self.cps_slider.blockSignals(False)
        
        if self.is_active and not self.hold_mode:
            self.stop_clicking()
            self.start_clicking()
    
    def update_settings(self):
        """Обновление настроек"""
        self.mouse_button = mouse.Button.left if self.left_radio.isChecked() else mouse.Button.right
        self.hold_mode = self.hold_checkbox.isChecked()
        
        # Перезапуск если активен
        if self.is_active:
            self.stop_clicking()
            self.start_clicking()
    
    def update_hotkey(self, key_text):
        """Обновление горячей клавиши"""
        key_map = {
            'Option + -': 'option+-',
            'F6': 'f6',
            'F7': 'f7',
            'F8': 'f8',
            'F9': 'f9',
            'F10': 'f10',
            'F11': 'f11',
            'F12': 'f12',
        }
        self.hotkey = key_map.get(key_text, 'option+-')
        self.hint_label.setText(f'💡 Нажмите {key_text} для включения/выключения')
    
    def on_key_press(self, key):
        """Обработка нажатия клавиши"""
        try:
            # Добавляем клавишу в набор нажатых
            if hasattr(key, 'char'):
                self.current_keys.add(key.char)
            else:
                self.current_keys.add(str(key))
            
            # Проверяем горячую клавишу
            if self.hotkey == 'option+-':
                # Option (Alt) + минус
                if (Key.alt in self.current_keys or Key.alt_l in self.current_keys or Key.alt_r in self.current_keys):
                    if '-' in self.current_keys:
                        self.toggle_clicking()
            elif self.hotkey == 'f6' and key == Key.f6:
                self.toggle_clicking()
            elif self.hotkey == 'f7' and key == Key.f7:
                self.toggle_clicking()
            elif self.hotkey == 'f8' and key == Key.f8:
                self.toggle_clicking()
            elif self.hotkey == 'f9' and key == Key.f9:
                self.toggle_clicking()
            elif self.hotkey == 'f10' and key == Key.f10:
                self.toggle_clicking()
            elif self.hotkey == 'f11' and key == Key.f11:
                self.toggle_clicking()
            elif self.hotkey == 'f12' and key == Key.f12:
                self.toggle_clicking()
        except:
            pass
    
    def on_key_release(self, key):
        """Обработка отпускания клавиши"""
        try:
            # Удаляем клавишу из набора
            if hasattr(key, 'char'):
                self.current_keys.discard(key.char)
            else:
                self.current_keys.discard(str(key))
        except:
            pass
    
    def toggle_clicking(self):
        """Переключение режима кликов"""
        if self.is_active:
            self.stop_clicking()
        else:
            self.start_clicking()
    
    def start_clicking(self):
        """Запуск кликов"""
        self.is_active = True
        self.signals.status_changed.emit(True)
        
        if self.hold_mode:
            # Режим удержания
            self.mouse_controller.press(self.mouse_button)
        else:
            # Режим кликов - запускаем в отдельном потоке
            self.click_thread = Thread(target=self.click_loop, daemon=True)
            self.click_thread.start()
    
    def stop_clicking(self):
        """Остановка кликов"""
        self.is_active = False
        self.signals.status_changed.emit(False)
        
        if self.hold_mode:
            try:
                self.mouse_controller.release(self.mouse_button)
            except:
                pass
    
    def click_loop(self):
        """Цикл кликов - работает постоянно пока is_active = True"""
        interval = 1.0 / self.clicks_per_second
        while self.is_active and not self.hold_mode:
            try:
                self.mouse_controller.click(self.mouse_button)
                time.sleep(interval)
            except Exception as e:
                print(f"Ошибка клика: {e}")
                break
    
    def update_status(self, is_active):
        """Обновление статуса в UI"""
        if is_active:
            mode_text = "УДЕРЖАНИЕ" if self.hold_mode else f"{self.clicks_per_second} КЛИКОВ/СЕК"
            button_text = "ЛЕВАЯ ←" if self.mouse_button == mouse.Button.left else "ПРАВАЯ →"
            self.status_label.setText(f'🟢 ВКЛЮЧЕН\n{button_text} | {mode_text}')
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #4caf50;
                    color: white;
                    padding: 25px;
                    border-radius: 15px;
                    font-weight: bold;
                    font-size: 22px;
                }
            """)
        else:
            self.status_label.setText('⚪ ВЫКЛЮЧЕН')
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #f0f0f0;
                    color: #666;
                    padding: 25px;
                    border-radius: 15px;
                    font-weight: bold;
                    font-size: 22px;
                }
            """)
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        self.stop_clicking()
        self.keyboard_listener.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    # Настройка шрифтов
    font = QFont()
    font.setFamily('Segoe UI' if sys.platform == 'win32' else 'SF Pro Display')
    app.setFont(font)
    
    clicker = AutoClicker()
    clicker.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()