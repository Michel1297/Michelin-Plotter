# MICHELIN-PLOTTER

import sys
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel,
    QComboBox, QLineEdit, QPushButton, QSplitter, QFrame, QMenuBar,
    QAction, QSpinBox, QHBoxLayout, QColorDialog, QGridLayout, QInputDialog, QTextEdit, QToolButton
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QIODevice
from PyQt5.QtGui import QColor
import pyqtgraph as pg


class SerialReaderThread(QThread):
    new_line = pyqtSignal(list)

    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self._stop_requested = False

    def run(self):
        try:
            with serial.Serial(self.port, self.baudrate, timeout=1) as ser:
                buffer = bytearray()
                while not self._stop_requested:
                    if ser.in_waiting:
                        buffer.extend(ser.read(ser.in_waiting))
                        while b'\n' in buffer:
                            line, _, buffer = buffer.partition(b'\n')
                            try:
                                decoded_line = line.decode(errors='ignore')
                                values = list(map(float, decoded_line.strip().split(',')))
                                self.new_line.emit(values)
                            except ValueError:
                                continue
        except Exception as e:
            print(f"[Serial Error] {e}")

    def stop(self):
        self._stop_requested = True
        self.wait()


class EditableLabel(QLabel):
    def __init__(self, text, callback):
        super().__init__(text)
        self.setStyleSheet("color: white; font-size: 12px;")
        self.setAlignment(Qt.AlignCenter)
        self.callback = callback

    def mouseDoubleClickEvent(self, event):
        dialog = QInputDialog(self)
        dialog.setMinimumSize(300, 100)
        dialog.setWindowTitle("Editar etiqueta")
        dialog.setLabelText("Nuevo texto:")
        dialog.setTextValue(self.text())
        if dialog.exec_():
            new_text = dialog.textValue()
            self.setText(new_text)
            self.callback(new_text)


class PlotterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Michelin-Plotter")
        self.resize(1200, 700)
        self.num_channels = 4
        self.max_points = [500 for _ in range(self.num_channels)]
        self.colors = [QColor(0, 255, 255), QColor(255, 100, 100), QColor(100, 255, 100), QColor(255, 255, 0)]
        self.data_buffers = [[] for _ in range(self.num_channels)]
        self.plots = []
        self.labels_x = []
        self.labels_y = []
        self.thread = None
        self.channel_to_plot_map = [i for i in range(self.num_channels)]
        self.plot_assign_combos = []

        self.setStyleSheet("background-color: #1e1e1e; color: white;")

        self.init_ui()
        self.rebuild_plots()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(1000 // 60)

    def init_ui(self):
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        sidebar = QWidget()
        sidebar.setMinimumWidth(160)
        sidebar_layout = QVBoxLayout(sidebar)

        self.port_combo = QComboBox()
        for port in serial.tools.list_ports.comports():
            self.port_combo.addItem(port.device)

        self.baud_input = QLineEdit("115200")
        self.connect_button = QPushButton("Conectar")
        self.connect_button.clicked.connect(self.connect_serial)
        self.status_label = QLabel("⏳ Esperando conexión...")

        sidebar_layout.addWidget(QLabel("Puerto:"))
        sidebar_layout.addWidget(self.port_combo)
        sidebar_layout.addWidget(QLabel("Baudrate:"))
        sidebar_layout.addWidget(self.baud_input)
        sidebar_layout.addWidget(self.connect_button)
        sidebar_layout.addWidget(QFrame())
        sidebar_layout.addWidget(self.status_label)

        # Botón para mostrar instrucciones
        instructions_toggle = QToolButton()
        instructions_toggle.setText("📘 Mostrar Instrucciones")
        instructions_toggle.setCheckable(True)
        sidebar_layout.addWidget(instructions_toggle)

        self.instructions = QTextEdit()
        self.instructions.setReadOnly(True)
        self.instructions.setPlainText("Formato esperado: valores separados por comas\nEjemplo: 1.0,2.5,3.6,4.2")
        self.instructions.setVisible(False)
        self.instructions.setStyleSheet("background-color: #333; color: #ccc; font-size: 11px;")
        instructions_toggle.toggled.connect(self.instructions.setVisible)
        sidebar_layout.addWidget(self.instructions)

        sidebar_layout.addWidget(QLabel("Asignación de canal a gráfico:"))
        for i in range(self.num_channels):
            combo = QComboBox()
            combo.addItems([f"Gráfico {j+1}" for j in range(self.num_channels)])
            combo.setCurrentIndex(i)
            combo.currentIndexChanged.connect(self.make_plot_assignment_handler(i))
            sidebar_layout.addWidget(QLabel(f"Canal {i+1}:"))
            sidebar_layout.addWidget(combo)
            self.plot_assign_combos.append(combo)

        sidebar_layout.addStretch()

        self.plot_area = QWidget()
        self.plot_layout = QVBoxLayout(self.plot_area)

        splitter.addWidget(sidebar)
        splitter.addWidget(self.plot_area)
        splitter.setSizes([160, 1000])

    def rebuild_plots(self):
        for i in reversed(range(self.plot_layout.count())):
            widget = self.plot_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.labels_x.clear()
        self.labels_y.clear()
        self.plots.clear()

        grid = QGridLayout()
        container = QWidget()
        container.setLayout(grid)

        for i in range(self.num_channels):
            layout = QGridLayout()
            widget = QWidget()
            widget.setLayout(layout)

            title = EditableLabel(f"Canal {i+1}", lambda x: None)
            label_y = EditableLabel("Amplitud", lambda text, idx=i: self.set_ylabel(idx, text))
            label_x = EditableLabel("Muestras por segundo", lambda text, idx=i: self.set_xlabel(idx, text))

            plot = pg.PlotWidget()
            plot.setBackground("#1e1e1e")
            plot.showGrid(x=True, y=True)
            plot.setYRange(-1.1, 1.1)
            plot.setMouseEnabled(y=False)
            plot.getPlotItem().ctrlMenu = None

            self.plots.append(plot)
            self.labels_x.append(label_x)
            self.labels_y.append(label_y)

            control_row = QHBoxLayout()
            hz_label = QLabel("SPS:")
            hz_spin = QSpinBox()
            hz_spin.setMinimum(50)
            hz_spin.setMaximum(5000)
            hz_spin.setValue(self.max_points[i])
            hz_spin.setFixedWidth(80)
            apply_btn = QPushButton("Aplicar")
            apply_btn.setFixedWidth(70)
            color_btn = QPushButton("Color")
            color_btn.setFixedWidth(70)

            def make_apply(idx, spinbox):
                return lambda: self.apply_max_points(idx, spinbox.value())

            def make_color_picker(idx):
                return lambda: self.choose_color(idx)

            apply_btn.clicked.connect(make_apply(i, hz_spin))
            color_btn.clicked.connect(make_color_picker(i))

            control_row.addWidget(hz_label)
            control_row.addWidget(hz_spin)
            control_row.addWidget(apply_btn)
            control_row.addWidget(color_btn)
            control_row.addStretch()

            layout.addWidget(title, 0, 1)
            layout.addLayout(control_row, 1, 1)
            layout.addWidget(label_y, 2, 0)
            layout.addWidget(plot, 2, 1)
            layout.addWidget(label_x, 3, 1)

            grid.addWidget(widget, i // 2, i % 2)

        self.plot_layout.addWidget(container)

    def make_plot_assignment_handler(self, channel_index):
        def handler(new_plot_index):
            self.channel_to_plot_map[channel_index] = new_plot_index
        return handler

    def set_xlabel(self, idx, text):
        self.labels_x[idx].setText(text)

    def set_ylabel(self, idx, text):
        self.labels_y[idx].setText(text)

    def apply_max_points(self, index, value):
        self.max_points[index] = value
        self.data_buffers[index] = self.data_buffers[index][-value:]

    def choose_color(self, index):
        color = QColorDialog.getColor(self.colors[index], self, f"Selecciona color para Canal {index+1}")
        if color.isValid():
            self.colors[index] = color
            self.rebuild_plots()

    def connect_serial(self):
        port = self.port_combo.currentText()
        try:
            baud = int(self.baud_input.text())
        except ValueError:
            self.status_label.setText("⚠ Baudrate inválido")
            return
        self.status_label.setText(f"Conectando a {port} @ {baud}...")
        self.thread = SerialReaderThread(port, baud)
        self.thread.new_line.connect(self.handle_data)
        self.thread.start()

    def handle_data(self, values):
        for i in range(min(self.num_channels, len(values))):
            self.data_buffers[i].append(values[i])
            if len(self.data_buffers[i]) > self.max_points[i]:
                self.data_buffers[i] = self.data_buffers[i][-self.max_points[i]:]

    def update_plots(self):
        for plot in self.plots:
            plot.clear()

        for i in range(self.num_channels):
            target_plot_index = self.channel_to_plot_map[i]
            if 0 <= target_plot_index < len(self.plots):
                curve = self.plots[target_plot_index].plot(pen=pg.mkPen(self.colors[i], width=2))
                curve.setData(self.data_buffers[i])

    def closeEvent(self, event):
        if self.thread:
            self.thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PlotterWindow()
    window.show()
    sys.exit(app.exec_())
